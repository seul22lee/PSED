# Stage 0 — full-paper audits of the 24 triggered papers

**Unit of audit: the unique source entity, not the record node.** Point-level records
were collapsed by their originating curve before any review.

Stable entity key:

    {paper_id}|{fig_docling_index}|{printed_figure_number}|{panel}|{source_series}|{representation}

`representation` (`primary` / `as_measured` / `scaled` / `normalized` / `inset`) keeps
several depictions of the same underlying data distinguishable instead of silently
merging them.

## Scope achieved

| | |
|---|--:|
| triggered papers audited | **24 / 24** |
| record nodes covered | 2230 |
| **unique source entities** | **539** |
| node → entity inflation | **4.1×** |
| entities with a resolved PDF page | 450 / 539 |
| entities left explicitly unresolved | 93 |

## Classification (unique entities, all 24 papers)

| class | n | share |
|---|--:|--:|
| `discrete_experimental_sweep` | 190 | 35.3% |
| `unknown` | 93 | 17.3% |
| `simulation` | 83 | 15.4% |
| `experimental_profile` | 65 | 12.1% |
| `multi_output_measurement` | 39 | 7.2% |
| `continuous_trace` | 28 | 5.2% |
| `model_sweep` | 26 | 4.8% |
| `imported_literature_data` | 10 | 1.9% |
| `fit` | 5 | 0.9% |

**124 entities (23.0 %) are not experiments at all** —
simulation, model sweep, imported literature, or fit — yet all of them are currently
`Experiment` nodes.

### Evidence standard

No class was assigned from point count, curve smoothness, axis type, or a lone caption
keyword. Two independent signal families must agree, except where a single family is
*definitional* (an explicit `Model`/author-year label, a `simulated` source flag, a
spatial-coordinate x axis).

| confidence | n |
|---|--:|
| `corroborated` | 373 |
| `single_definitional_signal` | 73 |
| `conflicting_signals` | 70 |
| `insufficient_corroboration` | 23 |

Signal families: **M** caption/body modality · **Me** methods modality ·
**R** explicit run-structure statement · **I** sample/run identifier ·
**L** series-label semantics · **F** extraction source flag · **T** table linkage ·
**X** axis/series-axis structure. Point count and smoothness are recorded in
`weak_signals` and never vote.

## Per-paper: nodes vs unique cases

| paper | nodes | entities | ratio | corrected cases | experimental cases | unresolved |
|---|--:|--:|--:|---|---|--:|
| `10.1002_admi.202000318` | 132 | 17 | 7.8× | ≥17 | ≥14 | 0 |
| `10.1002_celc.201600139` | 189 | 17 | 11.1× | ≥17 | ≥17 | 0 |
| `10.1002_pssa.201532305` | 300 | 28 | 10.7× | ≥28 | ≥27 | 1 |
| `10.1007_s11671-010-9676-0` | 1 | 1 | 1.0× | ≥1 | ≥0 (≤0) | 1 |
| `10.1007_s12274-010-0066-9` | 1 | 1 | 1.0× | ≥1 | ≥0 (≤0) | 1 |
| `10.1016_j.mee.2018.01.027` | 2 | 2 | 1.0× | ≥2 | ≥0 (≤0) | 2 |
| `10.1016_j.mee.2018.01.033` | 1 | 1 | 1.0× | ≥1 | ≥0 (≤0) | 1 |
| `10.1016_j.sse.2022.108584` | 74 | 26 | 2.8× | ≥26 (≤26) | ≥0 (≤0) | 0 |
| `10.1021_acs.chemmater.2c01154` | 190 | 56 | 3.4× | ≥56 | ≥56 | 0 |
| `10.1021_acs.chemmater.2c02292` | 155 | 44 | 3.5× | ≥44 | ≥30 | 12 |
| `10.1021_acs.jpcc.9b08176` | 136 | 11 | 12.4× | ≥11 | ≥0 (≤0) | 2 |
| `10.1039_c5tc03561a` | 25 | 14 | 1.8× | ≥14 | ≥14 | 0 |
| `10.1039_c6dt03571j` | 44 | 26 | 1.7× | ≥26 | ≥10 (≤14) | 16 |
| `10.1039_c7ra07722j` | 240 | 30 | 8.0× | ≥30 | ≥28 | 0 |
| `10.1039_d0cp03358h` | 74 | 74 | 1.0× | ≥74 (≤74) | ≥42 (≤42) | 0 |
| `10.1039_d3dt01824e` | 54 | 30 | 1.8× | ≥30 | ≥15 (≤21) | 15 |
| `10.1039_d3ra05217f` | 218 | 36 | 6.1× | ≥36 | ≥10 | 26 |
| `10.1063_1.4867469` | 6 | 6 | 1.0× | ≥6 | ≥1 (≤1) | 5 |
| `10.1063_1.5028178` | 74 | 19 | 3.9× | ≥19 (≤19) | ≥4 (≤4) | 0 |
| `10.1116_1.4938104` | 78 | 12 | 6.5× | ≥12 | ≥4 (≤8) | 8 |
| `10.1116_6.0002154` | 75 | 26 | 2.9× | ≥26 | ≥24 | 1 |
| `10.1116_6.0002804` | 121 | 22 | 5.5× | ≥22 | ≥20 | 2 |
| `10.1186_s11671-015-0872-9` | 1 | 1 | 1.0× | ≥1 | ≥1 | 0 |
| `10.3762_bjnano.5.25` | 39 | 39 | 1.0× | ≥39 (≤39) | ≥5 (≤5) | 0 |

**Corpus totals across the 24 papers: ≥539 cases, of which ≥322 are experimental**,
versus **2230 record nodes** today.

Upper bounds are deliberately open for **230 entities**: those papers do
not enumerate their settings, and the digitised point count is digitisation density,
not a count of depositions. Using it as a bound is the original error and is not
repeated here.

## Pressure resolution at series/run scope

| applicable scope / status | entities |
|---|--:|
| `None/None` | 272 |
| `paper/resolved` | 87 |
| `paper/ambiguous` | 81 |
| `figure/ambiguous` | 44 |
| `panel/resolved` | 31 |
| `figure/resolved` | 24 |

* **142** entities have a single applicable pressure resolved at panel, figure or paper scope.
* **125** have several competing candidates at their narrowest applicable scope and are left ambiguous.
* **272** have no applicable pressure assertion at all — correctly absent, not a loss.

Every pressure assertion carries quantity type, symbol, value, unit, species,
reactant role, assertion status (direct/estimated/assumed/approximate/fitted), scope
and evidence. **Exposure products (`mTorr·s`) are typed separately and never returned
as pressures.**

## Stage 0 completion checklist

| requirement | status |
|---|---|
| all 24 triggered papers have a completed audit | ✅ 24/24 |
| every unique source entity classified or explicitly unknown | ✅ 539 entities, 93 explicit `unknown` |
| exact source evidence recorded | ✅ caption + body span + PDF page (450/539) + sample/run id where stated |
| pressure applicability resolved at series/run scope | ✅ per-entity scope + status + candidates |
| per-paper corrected case-count ranges | ✅ with open upper bounds where unresolvable |
| revised patch sequence supported by full-paper frequencies | ✅ see below |

## Limitations, stated rather than hidden

* **93 entities (17.3 %) remain `unknown`** — 70 with
  conflicting signals, 23 with only one signal family. They are reported as
  unknown, not guessed.
* **89 entities have no resolved PDF page** — the caption text in `document.md`
  differs from the PDF layer (ligatures, hyphenation) so the anchor failed.
* **230 sweep sizes are unbounded above.** Closing them needs per-point
  evidence (a table of settings, or marker-level re-reading) that this stage did not do.
* `0` entities were classed as duplicate representations. The
  `representation` key distinguishes them structurally, but only a caption clause
  saying "scaled"/"normalized" triggers the class, so duplicates described in other
  words are still counted as separate cases.


## Full-paper frequencies that support each patch stage

| stage | what the 24-paper audit shows | supported? |
|---|---|---|
| **1 — continuity gate before splitting** | **24** entities that are a single run/specimen were expanded into **452** record nodes (28 continuous traces, 65 profiles, 39 multi-output measurements) | **yes — largest single effect** |
| **2 — separate record kinds** | **124** entities (23.0 %) are simulation / model sweep / imported literature / fit, occupying **340** `Experiment` nodes; 10 are cited-work measurements mis-filed as this paper's model output | **yes** |
| **3 — pressure scope + Unicode fold** | 142 entities resolve a single applicable pressure; 125 are ambiguous at their narrowest scope; 272 have none applicable | **yes, but smaller than the record-level view suggested** |
| **4 — deterministic condition recovery** | 459 entities carry a named between-curve condition in `series_axis` + a value in the label | **yes** |
| **5 — per-series measurand** | confirmed on `10.1016_j.sse.2022.108584` F5a/F5b; 26 model-sweep entities share one panel `y` | **yes, narrow** |
| **6 — scoped binding** | 125 pressure ambiguities are all paper/figure-scope broadcasts with no narrower alternative extracted | **yes** |

### What the full-paper audit does NOT support

* **Splitting genuine sweeps is not the problem.** 190 entities
  (35.3 %) are real discrete sweeps where per-setting records are
  legitimate. Stage 1 must keep them.
* **A fixed point-count threshold is not defensible.** 63
  genuine sweeps have ≥15 digitised points and 24
  single-run entities have <15. Any threshold rule mis-classifies both directions.
* **Model records are not a migration regression** (established earlier from the frozen
  baseline: 119/663 = 17.9 % before, 13.6 % after).

