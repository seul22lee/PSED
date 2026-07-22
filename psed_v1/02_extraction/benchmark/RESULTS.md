# Input-scope benchmark — results

Run: `bench_extract.py --run` (8 Gemini calls, gemini-2.5-flash) → `bench_score.py`.
Silver standard = full-manuscript extraction; narrower scopes scored by **recall**
(how much of `full` they recover), per field. 3 papers (arts2019, yim2020,
ylilammi2018); yim2020 has no parsed abstract, so abstract-scope averages 2 papers.

## Per-field recall (mean across papers)

| field | full items | abstract | abs+concl | **evidence** |
|---|---:|---:|---:|---:|
| material | 15 | 83% | 60% | 65%* |
| process type | 6 | 50% | 42% | **75%** |
| structure | 40 | 12% | 10% | **40%** |
| precursor | 17 | 0% | 3% | **36%** |
| coreactant | 10 | 17% | 17% | **39%** |
| deposition temp | 3 | 0% | 33% | **67%** |
| quantitative | 163 | 15% | 12% | **69%** |
| claims | 172 | 19% | 16% | 19% |
| **mean** | | 24% | 24% | **51%** |

**evidence** = abstract + conclusion + figure/table captions + the paragraphs that
discuss them (~25-32% of full-text tokens). It is the clear winner: 2.1x the recall
of abstract, quantitative field at 69%, and HIGHER precision than full text —
for arts2019 it returned exactly the correct 4 materials (no intro TiN/TaN), so its
"65%*" is only an artifact of scoring against the noisy 6-material full standard.

Limits: claims stay at 19% (spread through discussion, not captions), and ~31% of
quantitative lives in tables/body not captured by captions+context.

## Ground-truth correction (user, verified) — the key finding

For **arts2019 the correct material set is 4** (SiO₂, TiO₂, Al₂O₃, HfO₂ — confirmed
by Kessels ref 99). The full-text extraction reported **6** because it also grabbed
`TiN`/`TaN`, which appear only in the **introduction** as background examples, not
in Arts's own experiments.

Consequences:
- The **abstract's material recall is really ~100%** (4/4), not 67% — the 67% was an
  artifact of the silver standard over-collecting background entities.
- The real weakness of full-text extraction is **precision, not recall**: it does
  not distinguish *this paper's experimental entities* from *background/citation
  mentions* (same root cause as instruments under `structure`).
- **Implication for the KB:** the extractor needs a **paper-scope / relevance
  filter**, and the ontology should tag entity **provenance/role**
  (studied-experimental vs background-mentioned). This matters for the whole
  pipeline, independent of input scope.

So the two scopes have different *profiles*, not just different recall:
**abstract = high precision, low recall** (names exactly the studied subject);
**full = high recall, lower precision** (complete but pulls in background).

## What it says (the direction is robust; exact % are not)

1. **Full manuscript is required for everything the KB actually needs.**
   Precursors (0% from abstract), deposition temperature (0%), the bulk of
   quantitative data (163 mentions, ~15% recovered), per-experiment structure
   detail, and claims (19%) only appear in the body. Quantitative / experiment /
   equation extraction **must** use full text.

2. **Abstracts reliably give only coarse triage: material (83%) + process type
   (50%).** That's "what is this paper about", nothing quantitative.

3. **abstract+conclusion ≈ abstract (both 24% mean) — the surprise.** Adding the
   conclusion adds essentially no structured data (it even lowers material recall
   via noise; the only gain is deposition-temp 0%→33%). So the earlier
   "abstract+conclusion for profiling" idea is **not worth the extra tokens** over
   a plain abstract.

## Decision → INPUT_SCOPE

The evidence scope changes the answer from the earlier "everything = full":

- **KB structured extraction** (experiment schema, quantitative, conditions,
  precursors, structures) → **evidence**: near-full recall (quant 69%), higher
  precision (no intro/background), ~1/4 the tokens. This also matches how the
  existing figure-anchored stage 06 already works (caption + contexts).
- **Equations** → **full** (governing equations live in theory/methods, not captions).
- **Claims / meta-analysis** → **full** (evidence recovers only 19%).
- **Coarse triage** (material + process classification) → **abstract** suffices.

Set in [../config.py](../config.py). Future: enriching the evidence slice with
full tables + results-section paragraphs should lift quant 69%→higher and close
the claims gap.

## Caveats
- **Small corpus (3 papers)** — read direction, not precise numbers.
- **Noisy silver standard.** Full-text extraction over-collects: `structure` has
  40 "items" incl. instruments (`Filmetrics F40-UV`, `motorized mapping stage`),
  which depresses structure recall and flags a real **extractor-prompt** issue
  (tighten field definitions) independent of scope.
- Raw per-(paper,scope) extractions live in [out/](out/); prompts in [prompts/](prompts/).
