# Figure 9 - one measurement, three representations

## Provenance chain (each link stated in the paper)
```
physical sample (7, 8, 9 for Series C; 8, 10, 11 for Series D)
  -> reflectometry measurement of film thickness along the channel
     -> as-measured saturation profile        Fig. 9a / 9d   x (mm)  vs  S (nm)
     -> scaled saturation profile             Fig. 9b / 9e   x/H     vs  S/N
     -> Type 1 normalized saturation profile  Fig. 9c / 9f   x/H     vs  normalized thickness
```

## Transformation definitions (verbatim)
> "The scaled saturation profile has the total growth divided by cycles as the vertical
> axis and the measurement distance x divided by the channel height H as the horizontal
> axis."

> "We call the distance scaled this way the dimensionless distance x~ (x~ = x/H)."

Type 2 normalisation (x = x/L) is defined separately, confirming that the authors treat
normalisation variants as *representations* of one profile, not as new measurements.

## Classification
Panels a/b/c are **C - transformations of the same underlying measurement data**:
* a -> b: per-cycle scaling of y (S -> S/N) and coordinate scaling of x (x -> x/H)
* b -> c: normalisation of the y axis

No new physical act occurs between panels. The same holds for d/e/f.

## Consequence
Treating panels as independent results triples the apparent experimental evidence for this
paper. Any statistic over "number of profiles" is inflated 3x.

## Observed PSED behaviour (read-only)
Fig 9 a,b,c -> 3 + 3 + 3 = **9 Experiments**; d,e,f -> **9 more**. Ground truth is
3 measurements (Series C) and 3 measurements (Series D), each rendered three ways.
