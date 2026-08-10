# Why the tests passed

> **STATUS** — The gaps below are now closed by `canonical/tests/test_extraction_coverage.py` (38 tests). See [REPAIR_REPORT.md](REPAIR_REPORT.md) section 4.


147 tests pass (134 canonical + 13 repo suites) with a multi-material paper
collapsed to one chemistry and 146 sweeps minting zero cases. This is not test
*weakness* — each suite does what it claims. The suites collectively verify
**transformation correctness** and never verify **extraction coverage or input
correctness**.

## What each suite actually asserts

| suite | raw series coverage | raw point-set coverage | curve-vs-point granularity | no orphaned series | no wrong many-to-one merge | multi-material figure chemistry | caption↔material consistency | precursor/coreactant consistency | count preserved by interpretation |
|---|---|---|---|---|---|---|---|---|---|
| `canonical/tests/test_units.py` | – | – | – | – | – | – | – | – | – |
| `test_rules.py` | – | – | – | – | – | – | – | – | – |
| `test_context.py` | – | – | – | – | – | – | – | – | – |
| `test_semantics.py` | – | – | – | – | – | – | – | – | – |
| `test_provenance.py` (canonical) | – | – | – | – | – | – | – | – | – |
| `test_live_and_comparison.py` | – | – | – | – | – | – | – | – | – |
| `test_stage0_regression.py` | – | – | **conditional only** | – | – | – | – | – | – |
| `03_corpus/scripts/test_provenance.py` | – | – | – | – | – | – | – | – | – |
| `test_chemistry_propagation.py` | – | – | – | – | – | **unit-level only** | – | ✔ (given a material) | – |
| `test_card_temperature.py` | – | – | – | – | – | – | – | – | – |
| `test_pressure_extraction.py` | – | – | – | – | – | – | – | – | – |
| `test_geometry_model_params.py` | – | – | – | – | – | – | – | – | – |
| `04_twin_mpc/*` (7 suites) | – | – | – | – | – | – | – | – | – |
| `01_ontology/*` | – | – | – | – | – | – | – | – | – |

**Every column is empty.** No test in the repository asserts raw-series
coverage, orphan absence, merge correctness, caption↔material consistency, or
count preservation.

## The two specific blind spots

### 1. `test_chemistry_propagation.py` tests the stage *after* the bug

It is a clean unit test of `resolve_experiment_chemistry(material, …)`:

```python
check("Al2O3 gets TMA, not DEZ", r.precursor, "TMA")
check("and ZnO gets DEZ",        rz.precursor, "DEZ")
check("method", r.resolution_method, "material_element_match")
```

Every case **supplies the material as a test input**. The function is correct
and the test proves it. The defect is that stage 05 supplies
`scout.materials[0]` as that input — one stage upstream of the first assertion.
A test whose fixture hands over the right answer cannot detect a caller that
computes the wrong one.

No test imports `05_figure_extract.py`, exercises `_classify_label`, or asserts
anything about `records.json[*]["material"]`.

### 2. `test_stage0_regression.py` asserts granularity *conditioned on class*

```python
def test_profiles_are_measurements_not_point_experiments(self):
    pr = [e for e in self.ents if e["classification"] == "experimental_profile"]
    for e in pr:
        self.assertEqual(e["experimental_case_count"], 1)
```

Every test filters by `classification` first, then checks the arithmetic for
that class. So:

- The two `Fitting result` curves are classified `experimental_profile`, so the
  test **requires** them to mint 1 case each — the test actively *enforces* the
  R3 defect. Correct behaviour (0 cases, typed `Fit`) would fail this test.
- The 146 zero-case sweeps are `discrete_experimental_sweep`, whose
  `CLASS_MODEL` entry is `"case": "from_evidence"`. No test asserts what
  `from_evidence` must yield, so 0 is as acceptable to the suite as 5.
- `test_unknown_entities_are_preserved_unsplit_and_unpromoted` asserts
  `experimental_case_count == 0`, which is satisfied whether or not the
  classification was right.

The suite verifies the *consequences* of a classification. It never verifies the
classification against the source.

## Why the recently-added suites also missed it

The instruction not to treat these as coverage evidence is correct, and here is
the concrete reason for each:

- **Condition precision** (150/150, two draws) samples from **bound condition
  assertions**. Its population is conditions, not curves. A curve with the wrong
  material still binds the right pressure from the right sentence — c1–c7 all
  pass. Material is not one of the seven criteria.
- **Condition completeness** (1,964/1,964 KG-visible) tracks assertions from
  source text to KG. Every one of the 19 curves *is* KG-visible; the metric is
  green precisely because nothing was lost. It measures the wrong axis.
- **Unit conversion / provenance / deterministic IDs** are properties of a
  record given its content. All hold on a record labelled Al2O3 that should say
  TiO2.
- **KG visibility** counts nodes. 19 PlotSeries and 19 Curve nodes exist for
  this paper — visibility is perfect and the diagnosis is still wrong.

Each of these is a *transformation-fidelity* metric. None is an
*extraction-fidelity* metric. A pipeline that faithfully transforms a wrong
input scores 100 % on all of them.

## How the suite could pass while both failures were live

1. **The corpus is the fixture.** `test_stage0_regression.py` reads
   `02_extraction/output/` directly. Regenerating the corpus regenerates the
   fixture, so any change that is internally consistent stays green — the tests
   move with the data instead of pinning it.
2. **No invariant ties output back to input.** There is no assertion of the form
   "every series in `figure_data.json` has exactly one entity" or "no entity's
   material contradicts its own caption". Both defects are invisible to any test
   that reads only the output.
3. **Classification is an unchecked premise.** All granularity tests take
   `classification` as given. R3 is not merely undetected — it is *required* by
   `test_profiles_are_measurements_not_point_experiments`.
4. **Chemistry is tested at unit level with a hand-supplied material.** The one
   suite that could have caught R4 asserts the correctness of the function that
   is already correct.

## Minimum tests that would have caught each defect

| defect | test that would have failed |
|---|---|
| R4 material collapse | for every paper: `set(records[*].material) ⊇ {materials named verbatim in a figure caption}`; would flag 4 figures across 4 papers today |
| R4, stronger | for every multi-material paper, assert no record's material is assigned by list position — i.e. `_classify_label` returned `else` **and** `len(scout.materials) > 1` ⇒ material must be `None`, not `mats[0]` |
| R3 fit promotion | assert no entity with `is_current_paper_experiment` has a series label matching `fit\|calc\|model\|simul\|theor\|predict\|approx`, unless the caption contradicts the label |
| R3, structural | assert a panel whose caption distinguishes "measured … and calculated …" resolves its series to at least two distinct `source` values |
| R2 zero-case sweeps | assert `discrete_experimental_sweep` entities either mint ≥1 case or emit an `ExperimentSeries` row **and** are reported in a count that consumers read |
| R1 surface | assert `len(entities) == len(experiments) + len(series) + len(non_experimental)` per paper, and publish it |
| coverage, general | assert `sum(series in figure_data) == len(records) == len(entities)` per paper — passes today (659/659/663) and would have proven no loss occurred without any manual tracing |
