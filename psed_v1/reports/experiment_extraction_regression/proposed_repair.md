# Proposed repair

> **STATUS** — Superseded. P1-P4 were implemented (plus a fifth fix this proposal did not anticipate: model parameters scoped to their material). See [REPAIR_REPORT.md](REPAIR_REPORT.md).


Four independent defects (R1–R4 in `root_causes.md`). Each is separable and can
be approved, deferred or rejected on its own. None requires re-running plot
extraction or vision calls; all inputs are already on disk.

Ordered by evidence strength, not by size.

---

## P1 — figure-level material from the caption (fixes R4)

**Change**: in `05_figure_extract.py`, add a caption-material rung *above* the
paper-level fallback, and make the fallback refuse when it cannot be right.

```
precedence for a series' material:
  1. series legend label that is a paper material   (exists today)
  2. NEW: material named verbatim in this figure's caption, restricted to
     scout.materials, when the caption names exactly one
  3. NEW: scout.drill[F<idx>].why, same restriction
  4. single-material paper -> that material
  5. multi-material paper, no figure-level evidence -> None
```

Rung 5 is the essential half. `resolve_experiment_chemistry(None)` already
returns `ambiguous / unresolved_multi_material / confidence 0.0`, so refusing
produces an honest unresolved record instead of a confident wrong one. The
chemistry layer needs no change at all.

**Scope**: 9 multi-material papers. 4 figures gain a correct material
immediately; the rest of those papers' figures move from "confidently wrong or
accidentally right" to either correct or explicitly unresolved.

**Risk**: some records that are *accidentally* correct today (single-material
figures in a multi-material paper whose caption omits the material) will become
`None`. That is a deliberate recall loss for precision, consistent with the
existing "prefer ambiguity over an unsupported guess" rule. Quantify before
merging: count records that would go `mats[0] → None` per paper.

**Evidence requirement**: matching must be verbatim and anchored on
`scout.materials`, with docling's spaced formulas tolerated (`Al 2 O 3`).
Never infer a material from a precursor, and never from element overlap at this
stage.

---

## P2 — series-level measured-vs-calculated (fixes R3)

**Change**: resolve `source` per *series*, not only per figure/panel.

Two evidence sources, both already extracted:

1. **Caption legend mapping** — a caption of the form "measured (circles) and
   calculated (line)" assigns a source to each *marker style*. Where the
   extractor records marker style per series this maps directly; where it does
   not, the label usually carries it.
2. **Series label** — `Fitting result`, `Approximation`, `Gordon model`,
   `Calculated`, `Model` are self-identifying. Today these decide nothing.

Then: a series resolved as calculated inside a `measured` figure becomes a
`Fit` (when the caption ties it to the measured curve, as here) or a
`ModelPrediction` — and is **linked to** the measured run rather than minting
its own `ExperimentalCase` / `DepositionRun` / `Sample`.

**Scope**: 2 entities corpus-wide today. Small, but it is the only *regression*
of the four, and it corrupts the deposition count of the flagship conformality
paper 2×.

**Risk**: low. A label-based rule must not fire on a legend that merely
*contains* a substring (a sample named "Model A"); require the caption to
corroborate, per the existing multi-signal rule that weak signals never decide
alone.

**Blocked by**: `test_stage0_regression.py::test_profiles_are_measurements_not_point_experiments`
currently *requires* the wrong behaviour. That test must be amended in the same
change — it asserts the arithmetic for a class without checking the class.

---

## P3 — make the experiment surface complete (fixes R1)

**Change**: no pipeline logic. Emit a per-paper reconciliation alongside the
existing files:

```
entities = experiments + series + non_experimental
   663    =     316     +   146  +       201
```

and have every consumer that today reads `experiments.json` alone
(dashboards, corpus status, `kb_service`) read the reconciliation instead, or
state plainly which surface it is showing.

**Scope**: whole corpus. Zero data change.

**Why it matters**: this is what made a correctly-preserved 19-curve paper look
like a 4-record paper. Until a consumer can see 663 = 316 + 146 + 201, every
future audit will re-open this same investigation.

---

## P4 — resolve sweep case counts (fixes R2) — needs a decision, not a patch

146 of 151 discrete sweeps mint 0 cases because `supported_setting_count` only
counts *explicit sample lists*, which almost no paper provides.

Three options, in increasing order of risk. **I recommend (a), and (b) only with
per-paper verification.**

**(a) Consume the lower bound that already exists.** Each such entity carries
`experimental_case_lower_bound: 2` and an `ExperimentSeries` row. Report
"≥ N experiments" corpus-wide instead of silently contributing 0. No new
inference, no new evidence, no risk of fabrication. This alone restores an
honest corpus count.

**(b) Widen the evidence for `supported_setting_count`.** Add methods-table
enumeration and caption-enumerated settings ("at 200, 250 and 300 °C") as
additional *explicit* sources, keeping the existing rule that prose near an
unrelated figure never counts. Each new source must be validated against the
papers before it is trusted — the previous prose rule was removed precisely
because it matched "at 180 and 200 °C" for an ozone figure.

**(c) Infer from distinct x values.** **Reject.** This is the point-count rule
under another name; `distinct_setting_values_observed` is digitisation density.
Marker spacing was already tested and rejected (cv = 0.00 for both a genuine
6-temperature sweep and a 41-point interpolated curve).

**Scope**: 146 entities, 16 papers. The largest single contributor to the
perceived collapse.

---

## What must NOT be encoded as a universal rule

From the figure-by-figure resolution, these five are decided per figure and any
global rule would break at least one figure in this one paper:

1. A spatial x axis fixes curve-vs-point granularity but says nothing about
   measured-vs-modelled (Fig. 4 is spatial and calculated).
2. An enumerated condition axis implies separate runs only when the paper says
   something was *deposited* at each setting (Fig. 4's four channel heights are
   model inputs).
3. Two curves in one panel are not two experiments (Figs. 6, 7 are one
   measurement plus its fit).
4. A series axis is not always a process condition (Fig. 5's axis is model
   identity).
5. Figure-level `source` must not propagate unconditionally to its series
   (Figs. 6, 7 are `measured` figures containing a calculated curve).

---

## Sequencing

P3 first — it is zero-risk, and without it neither the current state nor any
repair can be verified by looking at the output. Then P1 (largest correctness
gain, self-contained), then P2 with its test amendment, then P4(a). P4(b) only
after per-paper verification of each new evidence source.

Each of P1, P2, P4 needs the corresponding coverage invariant from
`test_gap_analysis.md` added in the same change, or the next regeneration will
lose the guarantee again.
