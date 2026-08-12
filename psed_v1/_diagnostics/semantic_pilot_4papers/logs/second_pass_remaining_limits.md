# Limitations remaining AFTER the second-pass corrections

Only what is still true. Items the correction pass closed are not listed.

1. **Cross-figure case linking still needs an explicit statement.** `am.2016.182` reports
   50 cases for 16 curves and `2.067203jes` 23, because most of their sweeps carry no
   linkage statement. This is correct under "missing ≠ same" but it is not the number of
   depositions those papers performed. Only 4 of the 94 unresolved links are of a class the
   source could resolve.

2. **Specimen identity still depends on a machine-readable specimen table or a value-
   joinable legend.** Only Yim has one; the other three papers produce zero Samples. The
   value join now works, but it needs a table column to join against.

3. **Case-level geometry is proven on one figure.** The mechanism reads geometry from a
   figure caption and labels the paper-level fallback as a default, and JES Fig 8 exercises
   it. Papers that describe geometry only in prose still fall back.

4. **The intermediate device is not an object.** c7ta's replica-coated electrode is
   represented as a step inside a provenance chain, not as a `Sample`. The chain names the
   device, but a query for "what was measured" gets a chain record rather than a specimen.

5. **`text_cases` recognises one contrastive construction** — a per-cycle process
   repetition. Other papers will state process variants differently.

6. **Two upstream extraction defects remain worked around, not fixed**: the production
   caption grammar rejecting `( a )`, and the missing Docling crop for c7ta Fig 8(b).
   A third is now visible: production's condition parser reads a range separator as a minus
   sign, which the pilot repairs downstream rather than at source.

7. **The instrument lexicon and the column-header map are keyword lists.** Generic, but not
   complete. A quantity with no ontology `recipe_role` and no instrument term stays
   UNRESOLVED, and a specimen-table column whose header is unrecognised is carried opaquely.

8. **`_stem` is a suffix stripper, not a stemmer.** It matches "tubular" to "tubes"; it will
   not match irregular morphology.

9. **Counts remain incomparable across the boundary.** A PSED "Experiment" and a pilot
   "ExperimentalCase" are different objects. Any consumer reporting experiment counts would
   need its unit restated before a corpus migration.

10. **One JES image-supported case is coarse.** Printed Fig 3's TEM stack image yields a
    case carrying 200 cycles and 200 °C with both materials DEPOSITED. The caption states
    "10-40 cycles each" for the alternating layers, which the repair layer reads as a range
    elsewhere but which this path resolves to the figure's other cycle number. It is
    honest but not precise.
