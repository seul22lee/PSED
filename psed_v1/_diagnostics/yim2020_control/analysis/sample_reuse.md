# Sample reuse across author-defined Series

## Verified from Table 1
```
sample 8   (H=500, v1b, 500 cycles, 0.1-4.0-0.1-4.0)
    -> Series C   (variable: design channel height; members 7, 8, 9)
    -> Series D   (variable: ALD cycles;            members 10, 8, 11)

sample 12  (H=500, v1b, 500 cycles, 0.1-4.0-0.1-4.0)
    -> Series E   (variable: TMA pulse time; members 12, 13, 14)
    -> Series F   (variable: purge time;     members 15, 12, 16)
```
Both reused samples are the *reference/centre point* of their series: sample 8 is the
500 nm channel in C and the 500-cycle point in D; sample 12 is the 0.1 s TMA point in E
and the 4.0 s purge point in F. Sample 8 is additionally the Fig. 8a repeatability sample.

## Answer
**Series is an analytical grouping, not an ownership hierarchy.** A Series is defined by
*which variable the authors chose to vary*, and one physical sample can legitimately serve
as a member of several such comparisons at once. Membership is therefore many-to-many.

A model in which `ExperimentSeries` *contains* Experiments as exclusive children cannot
represent sample 8 without either duplicating it or arbitrarily assigning it to C or D.
