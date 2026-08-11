# Yim 2020 vs the previous three-paper audit

The earlier audit concluded that current PSED `Experiment` is a *result-local curve or
sweep point plus inferred conditions*, and that condition-case identity is generally
recoverable while run and specimen identity usually are not.

Yim 2020 **refines** that conclusion rather than confirming or contradicting it.

## Where it confirms
Observed PSED output for this paper (already corpus member `10.1039_d0cp03358h`):
39 Experiments, 70 entities, **0 series**, 37 distinct physical_case_ids, **none spanning
more than one printed figure**. Identity is again figure/panel-local.

## Where it refines
The earlier audit found specimen identity "rarely recoverable". Yim 2020 shows that in a
well-documented paper **all three levels are explicitly stated**:
* run identity - "All of the films were grown in the same ALD run" (Series A)
* specimen identity - "in the same sample" (Fig. 5b, sample 11); "sample 8" (Fig. 8a)
* condition-case identity - Table 1 gives every parameter per sample code

The earlier ceiling is therefore a property of *those three papers*, not a universal limit.
A representation unable to express run or specimen identity discards information that good
papers do publish.

## New distinctions this paper forces
1. **MeasurementCondition != DepositionCondition** (Series B: reflectometer magnification)
2. **Representation != Measurement** (Fig. 9 a/b/c, d/e/f)
3. **Series membership is many-to-many** (samples 8 and 12)
4. **Repeatability != reproducibility** (Fig. 8a vs 8b)
5. **ModelRun != Experiment** (Fig. 10) - PSED already handles this correctly
   (31 SimulationRun entities, records labelled simulated)
