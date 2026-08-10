# Corrections and qualifications to the diagnosis

Ten corrections requested after review. All are read-only; no pipeline output changed.

## 1. PSSA Fig. 4 arithmetic — CORRECTED

My earlier "232 records from 10 depositions" was wrong.

| | records | curves |
|---|--:|--:|
| **Fig. 4 (a–d)** — in-situ SE traces | **220** | 10 |
| Fig. 10a — also in-situ ("In-situ monitoring … by SE") | 48 | 1 |
| Fig. 6a — CVD growth rate vs process pressure | 3 | 1 |
| Fig. 9a — CVD growth rate vs process pressure | 4 | 1 |
| Fig. 11a — at-H pulse time | 7 | 1 |
| Fig. 11c — post at-H purge time | 5 | 1 |
| **point-level subtotal** | **287** | **15** |
| non-series: 8 `unresolved` (F2a, F5a×6, F11b) + 5 `profile` (F7a, F12a×4) | 13 | 13 |
| **total** | **300** | |

The **67** non-Fig-4 point-level records break down as 48 + 3 + 4 + 7 + 5. They are
**not** one failure mode:

* **Fig. 10a (48)** — same defect as Fig. 4. Caption: *"In-situ monitoring of HWALD
  growth in the linear regime by SE; the inset shows stepwise growth for individual
  cycles."* One run, 48 digitised points, 48 records.
* **Fig. 6a (3), Fig. 9a (4)** — *"CVD growth rate versus process pressure"*. Discrete
  pressure settings; splitting is **plausibly correct**.
* **Fig. 11a (7), Fig. 11c (5)** — *"Determining HWALD windows. Influence of: (a) at-H
  pulse time … (c) post at-H purge time"*. Process-window sweeps; splitting is
  **plausibly correct**.

So for this paper the over-split is **268 records from 11 continuous traces**, and
**19 records from 19 plausibly separate runs**. A corrected representation would hold
roughly 11 + 19 + 13 = **43 records**, consistent with your ~30 expectation once the
`unresolved` and `profile` records are re-examined.

## 2 + 3. Classification method — ADDED, and the earlier verdicts DOWNGRADED

The previous 120 verdicts were **not** paper-ground-truthed. They came from a caption
regex plus an n_points threshold. Every record now carries `classification_method`:

| method | records | underlying cases |
|---|--:|--:|
| `paper_verified` (exact span **and** a sample/run identifier) | 2 | 2 |
| `caption_inferred` (exact quoted span, no per-run id) | 51 | 42 |
| `metadata_inferred` (pipeline flag mirroring the paper) | 16 | 15 |
| `heuristic` (**not** ground truth — no decisive span found) | **51** | **40** |

Point count alone no longer produces a yes/no verdict. Records with no decisive span
are now `uncertain` + `heuristic`, which is why `uncertain` rose from 34 to
51. Every non-heuristic verdict stores its quoted span, the document
section, and why the points are one run or separate depositions
(`record_rereview.csv`).

**`source_pdf_page` could not be populated**: docling emits no page index in
`document.md` or `structure.json`. Layer-1 evidence is the caption plus the figure's
body mentions, not a PDF page. This is a real limitation of the audit.

## 4. Two levels reported separately — record node vs underlying case

| level | n | yes | no | uncertain |
|---|--:|--:|--:|--:|
| **current record nodes** | 120 | 13 | 56 | 51 |
| **deduplicated underlying cases** | 99 | 13 | 46 | 40 |

The record-level figure must **not** be read as "the fraction of actual experiments":
it is diluted by however densely each curve happened to be digitised. The
underlying-case level is the meaningful denominator, and there
40/99 cases are still undetermined.

I withdraw the earlier "9.2 % are physical experiments" headline.

## 5. Binomial intervals — REMOVED

Wilson/binomial intervals assumed i.i.d. draws. The design is three-stage and
unequal-probability (2-per-paper quota + proportional allocation + coverage top-ups),
so small papers are heavily over-sampled and records within a paper are correlated.

Replaced with a **Horvitz–Thompson ratio estimator** using Monte-Carlo inclusion
probabilities (400 replications of the
exact sampler) and a **paper-level cluster bootstrap**
(2000 replicates):

| metric | sample | HT population est. | cluster bootstrap 95 % |
|---|---|--:|---|
| record supported as a physical experiment | 13/120 = 10.8% | 10.7% | 4.2–18.6% |
| record NOT a physical experiment | 56/120 = 46.7% | 49.1% | 30.4–66.6% |
| record uncertain | 51/120 = 42.5% | 40.2% | 24.7–59.3% |
| record is model / simulation | 18/120 = 15.0% | 14.3% | 3.2–30.3% |
| record is one point of a continuous run | 30/120 = 25.0% | 31.7% | 10.6–51.3% |
| verdict backed by an exact span | 53/120 = 44.2% | 52.5% | 32.5–69.1% |
| pressure applicable **and** lost | 30/120 = 25.0% | 27.0% | 8.3–46.0% |

The intervals are much wider than the binomial ones I reported before — correctly so.

## 6. Pressure loss — RECOMPUTED with an applicability test

Previously any record in a paper with a non-empty `pressure.json` or a caption
pressure counted as a loss. Now a pressure counts only when it demonstrably applies
to that record (panel condition → figure caption → paper methods → single
unambiguous process pressure).

| | records | share |
|---|--:|--:|
| a pressure applies to the record | 60 | 50.0 % |
| … and is correctly bound | 30 | 25.0 % |
| … and is **lost** | **30** | **25.0 %** |
| no pressure applies (correctly absent) | 60 | 50.0 % |

Population estimate of applicable-and-lost: **27.0 %**
(bootstrap 95 % 8.3–46.0 %).
The earlier 26.7 % happened to land close, but for the wrong reason — half of its
numerator was records to which no pressure applied.

## 7. Baseline attribution — CORRECTED, and it exonerates the migration

| | records | model-labelled |
|---|--:|--:|
| **before** the granularity migration | 663 | **119 (17.9 %)** |
| **after** | 2457 | 335 (13.6 %) |

**Model curves were already stored as experiment-like records before the migration.**
Category **S** is a *pre-existing* defect, not a regression I introduced. The model
share actually *fell*, because the split inflated experimental records faster.

What the migration did do is expand model curves point-wise in exactly three papers:

| paper | model records before → after |
|---|---|
| `10.1021_acs.jpcc.9b08176` | 9 → 122 |
| `10.1063_1.5028178` | 15 → 70 |
| `10.1016_j.sse.2022.108584` | 26 → 74 |

So the new regression is **+216 model records from point-level expansion**, not the
storage of model curves as experiments. My earlier statement that "the
model-as-Experiment problem is mine" was wrong; only the expansion is.

## 8. Full-paper audits — NOT COMPLETED

24 of 31 papers met the §K trigger conditions. **None of the
24 full-paper audits was performed.** Only the 120-record random
sample, the targeted set and the two deep case studies are complete.

**Under the requested protocol the diagnosis is therefore not yet complete.** The
random-sample estimates stand on their own, but any claim about a specific triggered
paper beyond the two case studies is unsupported.

## 9. Deterministic pressure recovery — FEASIBLE; LLM proposal withdrawn

Over the 13 papers with a pressure in `document.md` and an empty
`pressure.json`:

| | |
|---|--:|
| pressure mentions found deterministically | 32 |
| value + unit resolvable deterministically | **32 (100 %)** |
| symbolic `p_A` / `p_A0` / `p_B` forms recovered | 4 |
| exposure products correctly separated from pressures | 1 |
| residual ambiguous (no figure anchor, no status cue) | 18 |

Both case studies are fully recoverable without an LLM:

* SSE: `p_A = 325 mTorr` *estimated*, `p_A = 160 mTorr` *estimated*, and
  `750 mTorr·s` correctly classified as an **exposure**, not a pressure;
* D0CP: `p_A0 = 65 Pa`, `p_B = 300 Pa`, `3 hPa` *approximate*.

**One prerequisite discovered while testing this:** docling writes symbols as
Mathematical-Italic Unicode, so the literal text is `\U0001D45D \U0001D434 = 325 mTorr`,
not `p_A = 325 mTorr`. Any deterministic parser must fold `U+1D400–U+1D7FF` to ASCII
first. Without that fold the SSE symbolic pressures are invisible — which is one
reason `10_pressure.py` may have found nothing.

**Two things the prototype does NOT yet do reliably**, and they must not be
overstated:

* **species binding** — the prototype mis-assigned `p_A → "325"` and `p_B → "TMA)"`;
  the species regex needs caption-structure awareness, not a character window;
* **figure applicability** — 0 of 32 mentions got a figure
  anchor from a ±220-character window. Caption-scoped parsing (parse *within* a
  caption, inherit that figure) will fix this, but it is unimplemented.

Revised LLM estimate: **0 calls for value/unit/status**, and at most
**18 residual mentions** for review *after* the deterministic
pass, not 13 whole-paper calls.

## 10. No pipeline outputs were modified

`git status` shows only the untracked `reports/condition_binding_diagnosis/`.

