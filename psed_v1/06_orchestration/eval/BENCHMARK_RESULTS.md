# Benchmark results — PSED KB (17-paper DOI-unified corpus)

Run on the DOI-unified corpus: **180 experiments · 17 papers · 16 materials** (Al2O3, BaO,
Er2O3, Fe2O3, HfO2, Ir, Li2CO3, Mo, Mo2N, MoOx, SiO2, SnO2, TiO2, Y2O3, ZnO, ZrO2). Every
paper is now identified by its **DOI** (e.g. `10.1063_1.5028178`); the 4 original papers
were re-extracted through the same scout-first 0709 protocol as the rest (old author-year
`output/` dirs kept under `output/_archive/`, unused). Ontology: 149 quantity kinds, 186
individuals; `electrical`/`composition`/`optical` categories added by the auto-propose loop.

All benchmarks are **deterministic** (KB queries + cached LLM answers); none call a live
model, so they reproduce exactly. Regenerate with the commands below.

---

## 1 · KB scorecard — 5 axes (`0706_pipeline/evaluate_kb.py`)

| axis | score | basis |
|---|---:|---|
| Conformance | 98% | 176/180 analysis-ready (4 quarantined: no-points) |
| Accuracy | 96% | axis-grounded; points 100%, material grounding weak (24%) |
| Coverage | 39% | 50/128 material×key-quantity cells |
| Consistency | 100% | derivation integrity holds |
| Inference | 67% | competency battery 4/6 answerable (penetration∝pulse^n, PD50, cross-validation pairs) |

**Overall 80%** (up from 77% at 10 papers). Note: re-extracting the 3 conformality originals
with the token-efficient 0709 protocol (scout-first, caption-gated) yields thinner
penetration profiles than the old exhaustive 0604 pipeline, so `consensus GPC Al2O3` is
currently not answerable — a real coverage effect of the protocol, not a regression bug.
| **Overall** | **77%** | coverage/inference rise as corpus scales |

Inference highlights (values no single record states): consensus GPC Al2O3 = 0.109 ± 0.003 nm
(n=7, 3% spread); penetration ∝ pulse_time^0.64 (diffusion-limited); PD50 = 568 (Arts 2019,
310 °C); materials with BOTH model & experiment for cross-validation: Fe2O3, Al2O3, SiO2, TiO2.

## 2 · Process identification — RSI 2026 Table VI (`eval/bench_process_id.py`)

KB-grounded identifier with **citations**, scored 0–1 on the paper's own rubric over a
12-challenge reconstructed subset.

**Our score: 0.92.** Fe2O3 now correctly resolved from the newly-ingested `admi.202000318`.

| system | score | | system | score |
|---|---:|---|---|---:|
| **ours (KB+cite)** | **0.92** | | o3 | 0.96 |
| avg reported LLM | 0.82 | | o1 | 0.94 |
| GPT-5 | 0.93 | | Claude Opus 4 | 0.93 |
| Claude Sonnet 4 | 0.85 | | GPT-4o | 0.72 |
| Gemini 2.5 Flash | 0.84 | | GPT-3.5 | 0.39 |

Reported LLM scores are Paper 2 Table VII, **cited not rerun**; ours is on a reconstructed
subset (indicative, not like-for-like vs their 30-challenge set).

## 3 · Geometry-aware conformal recipe design (`eval/eval_design.py`)

PSED extension beyond both Yanguas-Gil papers. Exposure-first (agent tunes **time**, pA
fixed by reactor), thickness step-coverage criterion, inverse procedure **validated against
a held-out KB profile** before use.

- Held-out validation (`ylilammi2018-F6-2`): twin 66.7 µm vs measured 127.6 µm → **k = 1.91×**
  calibration, carried into every design.
- Reactor (RSI Table I): pA = 100 Pa, T = 200 °C, N2; channels [TMA, water, DEZ, TDMAHf].
- Target: 90% thickness step coverage. Output is a full Argonne-JSON recipe (channels,
  ncycles, pulse, exposure Pa·s, purge, T) with chemistry cited to `aguinsky2023, yim2020, ylilammi2018`.

**vs real LLM baseline (Claude subagent, well-posed prompt):** the LLM returns a complete,
chemically-correct, exposure-aware recipe with caveats — the gap is **quantitative**: on a
3.3× AR increase the loop scales exposure ×13.7 (≈AR², data-anchored) while the LLM states
AR² but applies only ×1.25.

---

### Reproduce

```bash
PY=/home/ftk3187/miniconda3/envs/psed310/bin/python
$PY 0706_pipeline/evaluate_kb.py
$PY eval/bench_process_id.py        # → eval/process_id_results.json
$PY eval/eval_design.py             # → eval/design_results.json, eval/m5_design.html
$PY 0706_pipeline/benchmark/bench_score.py   # extraction-scope recall (silver = full text)
```

Extraction-scope recall (separate axis, 3-paper slice): **evidence** scope wins at 51% mean
recall (2.1× abstract) at ~25–32% of full-text tokens — quantitative field 69%.
