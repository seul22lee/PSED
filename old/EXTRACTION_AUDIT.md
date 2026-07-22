# Extraction Audit & Strategy — all 194 experiments

Reviewed every experiment (24 paper–figure groups). This is what the corpus *is*,
where it's broken, and the strategy that follows.

## What the corpus actually is

- **It is one big conformality dataset.** ~85% of experiments are
  `position ~ film_amount` or `position ~ coverage` — film thickness / coverage
  vs. position along a high-aspect-ratio feature. This is the naturally-comparable
  core, spread across all 4 papers.
- **Model-vs-experiment pairing is everywhere.** ≥8 figures pair a *Measured*
  curve with a *Model / Fit / appr* curve on the same axes (ylilammi 11/15/16,
  aguinsky 7/9/10, arts 10, yim 8). The cross-validation capability is real and
  sitting in the data.
- **Cross-paper redigitization exists.** aguinsky2023 re-plots Arts-2019,
  Yim-2020 and Ylilammi-2018 data as comparison curves — so several experiments
  appear **twice** in our corpus (original + aguinsky's redigitization).

## Defects found (prioritized)

| # | Where | Count | Problem |
|---|-------|-------|---------|
| D1 | aguinsky fig-005 | 6 | model plot `Γₑᵥ/Γ₀ vs β₀` mis-canonicalized to `surface_coverage ~ surface_coverage`; points degenerate (0..0). **Garbage.** |
| D2 | ylilammi fig-012 | 8 | `surface_coverage` profiles with **0 points** (digitization failed) |
| D3 | yim fig-007, fig-010 | 5 | no coordinate, 0 points (sub-panels never digitized) |
| D4 | yim fig-011 | 3 | O/Al/Si composition depth profiles → **no measurand** (no quantity for atomic concentration) |
| D5 | yim fig-017b, fig-017c | 6 | **true duplicates** — identical point arrays repeated within the subfigure |
| D6 | arts fig-010 (+others) | — | `pulse_time` has **no family** → penetration-vs-pulse_time (the saturation / recombination analysis) isn't comparable |
| D7 | aguinsky 7/9/10 vs originals | ~14 | **cross-source duplication** — same experiment from two papers, not linked |

≈22 experiments are not truly analysis-ready (D1–D4); ≈20 are duplicates (D5, D7).
The remaining ~150 are sound conformality profiles.

## Strategy

### S1 — Quality gate (deterministic triage) — *highest value, do first*
Add `analysis_ready` (bool) + `issues[]` to every experiment in `s08`, computed
from the record: `no-points`, `no-measurand`, `measurand==coordinate`,
`degenerate-range` (min==max), `zero-family`. Non-ready experiments are **retained
but excluded** from comparison/meta-analysis/eval. This immediately quarantines
D1–D4 (~22) without deleting anything, and makes "analysis-ready" mean it.

### S2 — Deduplication
Detect identical `(series, rounded-points)` within a figure → collapse (fixes D5).
Across papers, detect matching curves and link with `reproduced_from`
(fixes D7) — keep both, but flag so meta-analysis counts the measurement once while
still allowing extraction cross-validation (does aguinsky's redigitization of Arts
match ours?).

### S3 — Canonical = normalized, with a **profile-derived reference** — *resolves the paused canonical question AND the Tier-3 problem*
The corpus is mostly **absolute** `film_thickness` (nm), while canonical is
`normalized_thickness` — which is exactly why 57 profiles were stuck at Tier-3
(missing `reference_thickness`). Fix: **default `reference_thickness` = film
thickness at the feature mouth (min-x point)** of the profile. Validated: 51/57
profiles have mouth ≥ 80% of max, so this is physically sound (the mouth is the
saturated/plateau thickness). Effect:
- ~57 profiles jump Tier-3 → **Tier-2**, so the *entire* conformality corpus
  collapses into **one comparable set** in `(dimensionless_distance,
  normalized_thickness)` across all 4 papers.
- Absolute `film_thickness` stays available; normalization is a *view*, computed,
  labeled "normalized by mouth thickness."
- Coverage family canonical `surface_coverage` is already 0–1; position canonical
  `dimensionless_distance` already works via `feature_height`.

**Verdict on the canonical question:** normalized IS the right canonical for
conformality (it's the field's standard — step coverage vs aspect ratio), *provided*
the reference is defined. The profile-mouth default supplies it. Keep absolute as
the raw measurand.

### S4 — Fill ontology gaps exposed by the audit
- Add a **time / dose-time family** (`pulse_time`, `plasma_exposure_time`,
  `exposure`) so penetration-vs-pulse_time saturation curves become comparable (D6).
- Add an **atomic_concentration / composition** quantity so EDS depth profiles
  (D4) get a measurand instead of being dropped.

### S5 — Re-digitize the empties (optional, later)
ylilammi fig-012 (8) and yim fig-007/010 (5) have no points — a targeted re-run of
stage 03 (plot-to-data) on those figures would recover them. Until then, S1 keeps
them out of analysis.

### S6 — Explicit model↔experiment pairing
Within a figure, link each `model` curve to its `experimental` twin (same
measurand+coordinate, different relevance) via `validates`/`predicts`. The data is
already structured for it (Measured + Model pairs), and it turns the abundant
pairs into automatic model-vs-data residuals — the payoff of a model-aware KB.

## Recommended order
**S1 (quality gate) → S3 (canonical reference) → S2 (dedup) → S4 (families)** are
the high-value core: S1 makes "ready" honest, S3 unifies the comparable set and
answers the canonical question, S2 stops double-counting, S4 widens comparability.
S5/S6 follow.
