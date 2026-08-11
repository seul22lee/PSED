# Representation / transformation

**Required**: as-measured / scaled / normalized depictions of ONE measurement are not new
experiments. Yim Fig 9 a/b/c and d/f prove this with stated formulas
(S -> S/N, x -> x/H, then normalisation).

**Ontology**: `PlotRepresentation` exists - "One depiction (as-measured / scaled /
normalized / inset) of an underlying measurement. Several ..." - plus
`DerivedRepresentation` and `represents_same_as: PlotRepresentation -> Measurement`.
`TransformationRule` / `TransformationExecution` provide the transformation machinery.

**Instantiation**: `PlotRepresentation` **0**; `DerivedRepresentation` **2** corpus-wide;
`represents_same_as` is instantiated 64 times but between *entities* and PlotSeries, not
with its declared domain.

**Observed cost**: Yim Fig 9 -> **18 Experiments** for 6 measurements. Evidence for this
paper is inflated 3x.

**Status**: UNUSED_OR_UNINSTANTIATED; machinery already present. Gap type **A**.
Severity HIGH.
