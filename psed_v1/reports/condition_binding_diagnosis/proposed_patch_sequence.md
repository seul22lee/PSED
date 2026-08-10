# Revised patch sequence (v3)

> Updated after Stage 0 completed all 24 full-paper audits at **unique source entity**
> level (539 entities behind 2230 record nodes). Frequencies below are entity-level,
> not record-level. See `stage0/stage0_full_paper_audits.md`.

## What Stage 0 changed in this plan

1. **Stage 1's rule must not use a point-count threshold.** 63 genuine discrete sweeps
   have ≥15 digitised points and 24 single-run entities have <15 — a threshold
   mis-classifies in both directions. Replace it with the corroboration test actually
   used in the audit: ≥2 independent signal families, with a spatial-coordinate x axis
   as a structural gate.
2. **Stage 1's target is smaller and sharper than v2 assumed**: 132 entities
   (28 continuous traces + 65 profiles + 39 multi-output measurements) were expanded
   into 452 record nodes. 190 genuine sweeps must keep their per-setting records.
3. **Stage 2 grows in importance**: 124 entities (23.0 %) are not experiments at all
   and occupy 340 `Experiment` nodes.
4. **Stage 3 shrinks**: at entity scope only 125 pressure ambiguities exist, and 272
   entities have no applicable pressure at all (correctly absent, not a loss).
5. **A new Stage 7** is needed for the 93 unresolved entities.

# Superseded plan (v2) below


Supersedes v1. Changes forced by the corrections: model-as-Experiment is a
**pre-existing** defect not a migration regression (#7); pressure recovery is
**deterministic**, not an LLM job (#9); 40 % of underlying cases are still
**undetermined** (#2/#3), so no stage may assume a verdict the audit did not earn.

**Nothing here is implemented. Gate: complete the 24 full-paper audits (#8) before
Stage 2 ships.**

## Stage 0 (new) — finish the audit before patching

The protocol requires the 24 triggered full-paper audits; none were run. Stage 0 runs
them for the papers that dominate the record count (`10.1002_pssa.201532305`,
`10.1021_acs.jpcc.9b08176`, `10.1039_c7ra07722j`, `10.1039_d3ra05217f`,
`10.1021_acs.chemmater.2c01154`) and resolves the 40 heuristic-only underlying cases.
Read-only. Without it, Stage 1's continuity rules are tuned on 42 caption-inferred
cases, which is thin.

## Stage 1 — continuity test before splitting  (largest verified effect)

`06_to_kb.py::split_condition_series` + `canonical/live.py::axis_granularity`

Split a condition-axis curve into per-point experiments **only** when an exact span
supports separate runs. Three-way outcome, no silent default:

| evidence | action |
|---|---|
| continuity cue (`in situ`, ellipsometry/SE, QCM, `real-time`, depth profile, kinetics, impedance) | keep **one** `Observation` record |
| discrete cue (`independently varied`, `saturation curve`, `self-limiting`, `determining … window`, `as a function of <T\|pressure\|pulse\|purge\|dose>`) | split per point |
| neither | keep one record, flag `granularity_evidence = "none"` for review |

The third row is the change from v1: the audit found no decisive span for 40 of 99
underlying cases, so "no evidence" must not fall through to splitting.

Measured effect on `10.1002_pssa.201532305`: Fig. 4 (220→10) and Fig. 10a (48→1)
collapse; Fig. 6a/9a/11a/11c (19 records) survive. **Corpus effect is not predictable
in advance** — report it from the rebuild.

## Stage 2 — record kinds  (pre-existing defect, gated on Stage 0)

Emit `record_kind ∈ {ExperimentalCase, Observation, ModelRun, ImportedLiteratureProfile}`;
route `ModelRun` / `ImportedLiteratureProfile` out of `Experiment` in the KG.

Per-series source must beat the whole-figure flag: a legend with `<Author> <Year>`
marks `ImportedLiteratureProfile` + `reference_work`; `Model`, `Knudsen`, `Bosanquet`,
`simulat*` mark `ModelRun`. This fixes SSE Fig. 4, where `Arts 2019, 310 °C`
(literature *experiment*) is currently `relevance=model`.

Note the corrected attribution: this defect predates the migration (119/663 = 17.9 %
of baseline records were already model-labelled). The migration only expanded it
point-wise in 3 papers (+216 records), which Stage 1 already reverses.

## Stage 3 — pressure: deterministic first, scope precedence fixed

1. **Unicode fold** `U+1D400–U+1D7FF` → ASCII before any symbol parsing. Without it
   `p_A = 325 mTorr` is literally invisible. Cheapest, highest-yield line in the plan.
2. **Deterministic pressure/exposure parser** over `document.md` + captions:
   32/32 mentions across the 13 papers resolve to value + unit + status; the one
   `mTorr·s` product is correctly typed as **exposure**.
   *Prerequisites the prototype did not meet and must:* caption-scoped parsing so each
   mention inherits its figure, and structure-aware species binding
   (`p_A0 = 65 Pa (A = TMA)` → species TMA, not `"TMA)"`).
3. **Invert `_dedup_pressures`** — keep the narrower scope, attach the paper-scope
   duplicate as corroboration. One-line policy change; test on pssa Fig. 4.
4. Store `model_definition` pressures in a separate channel with
   `evidence_kind = model_input`, never as measured conditions.

**LLM calls: 0** for value/unit/status. At most **18 residual mentions** for review
after the deterministic pass — down from "13 whole-paper calls" in v1.

## Stage 4 — deterministic condition-mention recovery (0 LLM calls)

`extracted/{doi}/assertions/condition_assertions_v1.json` from a caption parser, a
legend parser, a figure-linked-text parser and a table joiner. All inputs already in
the repo. Fixes SSE Fig. 2/4/6/7 and D0CP Fig. 10.

## Stage 5 — per-series measurand (schema, category N)

Optional `series[].y = {quantity, unit}`; absent ⇒ inherit panel. SSE Fig. 5a/5b are
the proof cases. Deterministic label→quantity mapping covers every instance found, so
**0 vision calls** unless a new pattern appears.

## Stage 6 — scoped binding replaces broadcast

`ScopedConditionBinder` over the assertions, narrowest scope first, paper scope only
when unambiguous and nothing narrower exists. Reuses `canonical/context.py::ContextPool`.

## Explicitly NOT proposed

* No ontology redesign — not implicated in any sampled first-failure.
* No re-digitisation — 0/120 records need it.
* No rewrite of `figure_data.json` — all recovery additive.
* No corpus-wide LLM re-extraction.
* **No corpus rebuild until Stage 0 closes**, because 40 % of underlying cases are
  still undetermined and Stage 1's rules would be tuned on incomplete evidence.

## Regression tests (unchanged from v1, plus)

| test | asserts |
|---|---|
| `pssa Fig.4` / `Fig.10a` | in-situ traces stay 1 record each; caption `0.01 mbar` survives at figure scope |
| `pssa Fig.6a/9a/11a/11c` | discrete sweeps still split |
| `no-evidence curve` | a curve with neither cue stays **one** record and is flagged, not split |
| `unicode fold` | `\U0001D45D \U0001D434 = 325 mTorr` parses as `p_A = 325 mTorr` |
| `exposure vs pressure` | `750 mTorr·s` types as exposure, never pressure |
| `species binding` | `p_A0 = 65 Pa (A = TMA)` → species `TMA`; `p_B = 300 Pa (B = N2)` → `N2` |
| `sse Fig.4` | `Arts 2019, 310 °C` is `ImportedLiteratureProfile`, not `ModelRun`; Fig.2 geometry not broadcast |
| `sse Fig.5b` | `t_p`, `θsat`, `SCsat` distinct quantities; no point becomes an Experiment |
| `d0cp methods` | `3 hPa` retained; `pA0`/`pB` are model inputs, not measured conditions |


## Stage 7 (new) — close the 93 unresolved entities

Stage 0 left 93 entities (17.3 %) `unknown`: 70 with conflicting signals, 23 with a
single signal family. They are not distributed evenly — `10.1039_d3ra05217f` (26),
`10.1039_c6dt03571j` (16) and `10.1039_d3dt01824e` (15) hold 60 % of them.

These need per-figure human adjudication or a targeted table/marker read, not more
rules. Until they are closed, every corrected case count keeps an open upper bound and
no corpus rebuild should claim a final experiment count.
