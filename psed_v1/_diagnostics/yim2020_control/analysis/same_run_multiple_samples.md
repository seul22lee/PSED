# Series A — one ALD run, three samples

## Verified statement
> "To study the effect of the pillar density on the saturation profile, Al2O3 films were
> coated in LHAR channels with different pillar designs of layout v1a, v1b, and v2a
> (design channel height: 500 nm), which had been fabricated on the same silicon wafer.
> **All of the films were grown in the same ALD run to avoid run-to-run variations**
> (Series A in Table 1)." — Experimental §B

## Structure
| | sample 1 | sample 2 | sample 3 |
|---|---|---|---|
| pillar layout | v1a | v1b | v2a |
| channel height | 500 nm | 500 nm | 500 nm |
| cycles / sequence | 500 / 0.1-4.0-0.1-4.0 | same | same |
| ALD run | **RUN_A (one shared execution)** | RUN_A | RUN_A |
| GPC_IIb (nm) | 0.107 | 0.109 | 0.107 |
| x50% (um) | 140 | 140 | 110 |

One deposition **run**; three distinct physical **samples**; one deposition **condition
case** (the ALD recipe is identical); three different **sample geometries**.

## Information loss per candidate definition
* **Experiment = deposition run** → 1 Experiment. Loses the v1a/v1b/v2a distinction, which
  is the entire point of Series A (x50% moves 140 → 110 um).
* **Experiment = sample** → 3 Experiments. Preserves the layouts but loses the fact that
  they share one run, which is exactly the control the authors engineered.
* **Experiment = deposition-condition case** → 1 Experiment if geometry is excluded from
  the case key, 3 if pillar layout is part of it. Neither variant records the shared run
  unless run identity is carried separately.

**Conclusion.** No single level expresses Series A. Run identity and sample identity are
*independent* facts here, and the paper states both explicitly.
