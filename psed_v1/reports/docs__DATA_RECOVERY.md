# Data recovery — restoring axis semantics that extraction dropped

## 1. The problem

The historical figure-extraction schema (`03_corpus/scripts/05_figure_extract.py`)
asked the vision model for a **pre-mapped** quantity name from a fixed enum and a
unit string. It never captured the axis label as printed. So:

| printed on the axis | stored | information lost |
|---|---|---|
| `x̃ = x/H` | `spatial_coordinate`, unit `""` | that it is normalized, and by what |
| `Normalized distance ξ` | `spatial_coordinate`, unit `""` | same |
| `t(x)/t(0)` | `normalized_thickness`, unit `""` | which denominator |
| `Thickness/cycles S/N (nm)` | `growth_per_cycle`, unit `nm` | the `/cycle` dimension |

Without the denominator, a dimensionless distance cannot be compared with any
other paper's, and must not be assumed to mean anything in particular.

## 2. Recovery strategy, in priority order

Cheapest and most local first. Each step only runs when the previous left the
axis unresolved.

| # | Source | Confidence weight | Cost |
|---|---|---|---|
| 1 | verbatim axis label (once recovered) | 1.00 | — |
| 2 | panel-specific caption clause `(c) …` | 0.90 | — |
| 3 | whole figure caption | 0.80 | — |
| 4 | figure discussion in `document.md` (windows around each "Fig. N") | 0.55 | — |
| 5 | equation-like lines in `document.md` | 0.50 | — |
| 6 | **symbol definition** anywhere in the paper (`x̃ = x/H`) | 0.70 | — |
| 7 | selective vision re-read of the figure image | 0.95 | 1 LLM call/figure |

The panel clause is tried **before** the whole-figure caption: a caption naming
four different normalizations for four panels must resolve per panel, not come
back ambiguous for all of them.

### Symbol-definition resolution

Dimensionless axes usually print only a symbol (`x̃`, `ξ`) while the paper defines
it once, far away. The resolver extracts the axis symbol from the recovered label
and looks for `<symbol> = <ratio>` anywhere in the paper.

Matching is **diacritic-exact**: a paper that writes `x̃ = x/H` and `x = x/L` uses
the tilde as the discriminator, so `x̃` matches only the tilde form. Treating the
tilde as optional collapsed two real definitions into a false ambiguity — that
single fix took `x/H` recovery from 1 curve-axis to 36.

## 3. Selective re-extraction

Re-reading a figure costs a vision call, so it is spent only where it can unlock a
comparison group. `recover_axis_semantics.py` emits a prioritised work list
(`reports/canonical/reextraction_candidates.json`):

* **high** — a comparison-target axis whose semantics are blocked: normalized `y`
  with no definition, dimensionless spatial `x` with no denominator, conflicting
  semantics, or a unit whose dimension contradicts its quantity.
* **medium** — an unparseable unit on an axis that is not otherwise blocked.
* **low** — spectra (XRD/XPS/FTIR). Their axes are not comparison targets at all,
  so re-reading their labels would not make them comparable. Flagged for the
  record, not re-run.

The re-extraction schema captures **axis metadata only**:

```json
{"label_raw": "...", "unit_raw": "...", "is_normalized": true,
 "normalization_expression": "x/H", "normalization_denominator_symbol": "H",
 "axis_scale": "linear", "series_legend": [...], "annotations": [...]}
```

**Digitized points are never requested and never replaced** (`points_replaced:
false`, asserted by a test). Results land in a new versioned file,
`extracted/{doi}/recovery/figure_semantics_v1.json`; `figure_data.json` is never
written to.

## 4. Evidence-backed unit recovery

Two cases, both requiring the label to say so:

* the unit is printed in the label but was not captured — `GPC (Å/cycle)` with an
  empty unit field;
* the label divides by cycles while the unit is a bare length —
  `Thickness/cycles S/N (nm)` → `nm/cycle`.

A bare `GPC (nm)` with no division printed stays a **dimension conflict**
(`status: invalid`) and goes to the manual review queue. The missing `/cycle` is
never assumed.

## 5. What a recovery record carries

Source file, source location, figure and panel, the quoted evidence span, the
recovery method, a confidence, whether it was automatic or needs review, the
original value and the recovered value.

Assignments below confidence 0.6 are kept but flagged
`needs_manual_review: true` and listed in
`reports/canonical/manual_review_queue.json`.

## 6. Before expanding to ~80 papers

The single highest-value change is to **stop losing the labels in the first
place**: `05_figure_extract.py` should emit `label_raw`, `unit_raw`,
`is_normalized`, `normalization_expression` and
`normalization_denominator_symbol` per axis, exactly as
`reextract_figures.py` already does. That turns recovery from a repair pass into a
no-op for new papers.

Until then, every new paper needs the recovery + selective re-extraction steps in
[PIPELINE.md](PIPELINE.md) §2.
