# Root causes — experiment extraction regression

> **STATUS** — This diagnosis describes the state before the repair. All four root causes (R1-R4) are now fixed; see [REPAIR_REPORT.md](REPAIR_REPORT.md) for what changed and how it was validated.


Read-only diagnosis. No pipeline code, test, ontology, regenerated output or
prior report was modified. Everything here is reproducible with
`reports/experiment_extraction_regression/audit.py`.

---

## Headline: the reported symptom is real, the assumed mechanism is not

`10.1063_1.5028178` does show **4 rows in `experiments.json`** against **19 raw
extracted curves**. But no curve was deleted, merged, or orphaned:

| stage | count |
|---|---:|
| series in `figure_data.json` | 19 |
| records in `records.json` | 19 |
| source entities in `resolved/entities.json` | 19 |
| curves in `canonical/curves.json` | 19 |
| `PlotSeries` nodes in the KG | 19 |
| `Curve` nodes in the KG | 19 |
| rows in `resolved/experiments.json` | **4** |

Raw points vs. entity observations: **0 lost** (496 observations preserved, up
from the committed baseline's 227 — the current run keeps *more* data).

Corpus-wide the same holds: **659 raw series → 659 records → 663 source
entities, 0 orphans in all 31 papers.**

So this is not a data-loss bug. It is three separate defects that all narrow the
*experiment surface* while leaving the underlying curves intact. They must be
fixed independently; only R2 is a regression.

---

## R1 — `experiments.json` is not the experiment inventory (surface defect)

`experiments.json` emits a row only for an entity with
`experimental_case_count >= 1`. Everything else — model curves, sweeps with
unresolved settings, imported literature — lives in `entities.json` and
`series.json`. Corpus-wide:

| surface | rows |
|---|---:|
| `entities.json` (every source entity) | 663 |
| `experiments.json` | 316 |
| `series.json` | 146 |
| non-experimental typed entities (simulation / model_sweep / fit / literature / unknown) | 201 |

316 + 146 + 201 = 663. Nothing is missing; three files must be read together,
and no consumer or report says so. Any audit that reads `experiments.json` alone
will conclude the corpus lost two thirds of its records.

**Not a regression** — but it is why the loss appeared total.

---

## R2 — 146 of 151 discrete sweeps mint zero experimental cases (the real under-count)

[`06_to_kb.py:821-833`](../../03_corpus/scripts/06_to_kb.py#L821-L833):

```python
elif model["case"] == "from_evidence":
    n = cls["supported_setting_count"]
    if n:
        n_cases, case_status = n, "enumerated_in_source"
    else:
        n_cases, case_status = 0, "unresolved_settings"
```

`supported_setting_count` was deliberately narrowed to *explicit sample lists*
after prose matching produced false positives (it had matched "at 180 and 200 °C"
for an unrelated ozone figure). Almost no paper enumerates its sweep settings in
that exact form, so the guard fires almost always:

| | entities |
|---|---:|
| `discrete_experimental_sweep` with ≥1 case | **5** |
| `discrete_experimental_sweep` with 0 cases | **146** |

spread over **16 papers** (worst: `chemmater.2c01154` 27, `6.0002804` 23,
`6.0002154` 20, `chemmater.2c02292` 15, `c7ra07722j` 14).

The refusal is *honest* — the entity keeps `is_current_paper_experiment: True`,
`experimental_case_lower_bound: 2`, an explicit `experimental_case_reason`, and
an `ExperimentSeries` row in `series.json`. It is not honest *downstream*: a
sweep the classifier is confident about ("corroborated") contributes nothing to
the experiment count, and the lower bound of 2 is never used by any consumer.

This is the single largest contributor to the perceived collapse and it is
**strictly a granularity-evidence problem, not a classification problem**.

---

## R3 — calculated curves promoted to experiments (typing defect)

Figs. 6 and 7 each contain a measured profile and a calculated fit. The caption
says so verbatim:

> "The measured (**circles**) and calculated (**line**) thickness profiles…"

and the body states the mechanism:

> "An efficient analytic approximate solution of the diffusion equation is
> developed **for fitting the model to the measured thickness profile**."

Both series are nevertheless classified `experimental_profile` and minted as
full `ExperimentalCase` + `DepositionRun` + `Sample`:

| entity | series label | classification | should be |
|---|---|---|---|
| idx 14 | `Measured` | experimental_profile | ExperimentalProfile ✔ |
| idx 14 | `Fitting result` | experimental_profile | **Fit** of the same run |
| idx 15 | `Measured` | experimental_profile | ExperimentalProfile ✔ |
| idx 15 | `Fitting result` | experimental_profile | **Fit** of the same run |

Cause: the provenance gate reads `source` at **figure/panel** level only
(`panel_source = {"_fig": "measured"}`), so both series of a measured figure
inherit "measured". Series-level measured-vs-calculated evidence — present in
the caption *and* in the series label — is never consulted.

Consequence: the paper reports **4 depositions, 4 samples, 4 deposition runs**
where the body describes exactly **two** (Al₂O₃ 500 cycles, TiO₂ 1000 cycles).
So `experiments.json` is simultaneously under-inclusive (R1/R2) and
over-counting depositions 2× here.

Corpus-wide this is contained: a scan for calculation-like series labels
(`fit|calc|model|simul|theor|predict|approx`) typed as current-paper experiments
returns **exactly these 2 entities**.

---

## R4 — figure material is `scout.materials[0]` (chemistry corruption)

[`05_figure_extract.py:375`](../../03_corpus/scripts/05_figure_extract.py#L375)
and [`:383`](../../03_corpus/scripts/05_figure_extract.py#L383):

```python
material = (mats[0] if mats else None)   # mats = scout["materials"]
```

Material is recovered **only when the series legend label is itself a material
name** (`_classify_label` → `"material"` branch). For every other legend — a
numeric sweep value, a categorical name, or an empty label — the paper's *first*
material is assigned by list position.

For `10.1063_1.5028178`, `scout.materials = ["Al2O3", "TiO2"]`, and Fig. 7's
labels are `Fitting result` / `Measured` → neither is a material → both get
`mats[0] = "Al2O3"`.

The chemistry layer is **not** at fault. Called directly:

```
resolve_experiment_chemistry("Al2O3") -> TMA   , material_element_match, conf 0.7
resolve_experiment_chemistry("TiO2")  -> TiCl4 , material_element_match, conf 0.7
resolve_experiment_chemistry(None)    -> None  , unresolved_multi_material, conf 0.0
```

It resolves TiO₂ → TiCl₄ correctly and already prefers ambiguity over a guess
when the material is unknown. Stage 05 defeats that by supplying a *confident
wrong* material instead of no material.

### Which of the eight candidate causes is it

| hypothesis | verdict |
|---|---|
| paper-level primary material broadcast | **yes** — `mats[0]` for every non-material legend |
| first-item / list-order fallback | **yes** — same line; identical to the DEZ/Al₂O₃ bug the chemistry layer was written to fix, one stage earlier |
| caption chemistry not parsed | **yes** — no caption chemistry parse exists at any stage |
| caption chemistry parsed but overwritten | no |
| chemistry selected before figure material resolved | no — chemistry is keyed on material; the material is already wrong |
| element matching against the wrong material | **downstream symptom** — matching is correct, the input is wrong |
| multi-material paper collapsed to one chemistry | **yes** — the observable effect |
| provenance precedence reversed | **yes, structurally** — figure-level caption evidence has *no* precedence rung at all, so a paper-level fallback wins by default |

### The evidence was present and unread

The caption is carried into `records.json` provenance and is not truncated past
the relevant clause:

```
provenance.caption = "FIG. 7. The measured (circles) and calculated (line)
thickness profiles of a 1000cycle deposition process of TiO2 from TiCl4 and
H2O. The nominal channel gap height is 0.5 l m. …"
```

`scout.json` is also correct at figure granularity:

```
materials : ["Al2O3", "TiO2"]
drill F14 : source=measured, why="…thickness profiles of Al2O3 in lateral channel"
drill F15 : source=measured, why="…thickness profiles of TiO2 in lateral channel"
```

Every input needed for the right answer sits in the same record as the wrong
answer.

### Corpus-wide blast radius

**9 of 31 papers** are multi-material yet collapse to a single record material:

| paper | scout materials | assigned |
|---|---|---|
| `10.1116_1.4938104` | Al2O3, Pt, TiO2, ZnO, TiN, W | **Al2O3** (6 → 1) |
| `10.1021_acs.chemmater.2c01154` | MoS2, TiS2, WS2 | MoS2 |
| `10.1007_s12274-010-0066-9` | Pt, TiO2, Al2O3 | Pt |
| `10.1063_1.5028178` | Al2O3, TiO2 | Al2O3 |
| `10.3762_bjnano.5.25` | Al2O3, TiO2 | Al2O3 |
| `10.1016_j.tsf.2012.11.127` | ZrO2, Fe2O3 | ZrO2 |
| `10.1039_c5tc03561a` | BaO, BaTiO3 | BaO |
| `10.1039_c7ra07722j` | Li2CO3, Li2O | Li2CO3 |
| `10.1016_j.mee.2018.01.027` | Ir, Al2O3 | Ir |

`10.1021_acs.jpcc.9b08176` is the control: 4 materials, all 4 present in the
records — because there the legend labels *are* material names. That confirms
the mechanism exactly: material survives only via the legend, never via the
caption.

Figures whose caption names a material the records never assign
(`corpus_chemistry_conflicts.csv`): **4**, all high-confidence —
`1.5028178` Fig 7 (TiO2→Al2O3), `chemmater.2c01154` Fig 9 (TiS2→MoS2),
`1.4938104` Fig 5 (W→Al2O3), `bjnano.5.25` Fig 6 (TiO2→Al2O3).

### Not a regression

The committed baseline (`git show HEAD:…/experiments.json`) has 19 rows, **all
of them `Al2O3` / `TMA`**, including the pure-simulation figures. The chemistry
corruption pre-dates the entity/granularity repair by at least four commits. It
was inherited, not introduced.

---

## Before / after against the committed baseline

| | before (HEAD) | after (working tree) |
|---|---:|---:|
| `experiments.json` rows, corpus | 672 | 316 |
| raw series | 659 | 659 |
| source entities | — | 663 |
| orphaned raw series | — | **0** |

The −356 decomposes into model/simulation/literature reclassification (R1) and
sweeps with unresolved settings (R2). Per-paper detail, including the
reclassification breakdown, is in `removed_and_merged_records.json`.

- **removed experiment IDs**: none. `experiment_id` is `null` in both versions,
  before and after, so no ID was dropped — there were never any to drop. Records
  are matched by (figure, series, observation count), and every before-row has a
  corresponding after-entity.
- **merged experiment IDs**: none. The only many-to-one relation is
  `multi_output_measurement` (26 entities → shared identity in
  `chemmater.2c01154`), which is the intended contract behaviour: several
  observable channels from one sample share an experimental identity.
- **source curves with no current entity**: 0, corpus-wide.
- **point-level experiments incorrectly collapsed**: 146 sweeps (R2) — collapsed
  to 0 cases rather than to 1; their `ExperimentSeries` rows survive.
- **curve-level experiments incorrectly split**: 2 (R3) — the two `Fitting
  result` curves split their run into a second spurious ExperimentalCase.
- **model/calculated curves dropped**: 0. 201 are typed and preserved.

---

## Summary of causes by kind

| id | defect | kind | regression? | blast radius |
|---|---|---|---|---|
| R1 | `experiments.json` is a filtered surface with no companion index | reporting | no | whole corpus |
| R2 | sweeps mint 0 cases when settings are not enumerated in a sample list | granularity evidence | no (predates) | 146 entities / 16 papers |
| R3 | series-level measured-vs-calculated never resolved; fits promoted to experiments | classification | **yes** (introduced with the entity model) | 2 entities / 1 paper |
| R4 | figure material = `scout.materials[0]` | chemistry provenance | no (predates by ≥4 commits) | 9 papers, 4 hard caption conflicts |
