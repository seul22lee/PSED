# Conditions - deposition vs measurement

**Required**: Yim Series B varies reflectometer magnification (50x/10x/5x, spot 5-50 um)
with identical deposition parameters. A measurement condition must never define a
deposition case.

**Ontology**: `ConditionAssertion` carries "value, evidence, assertion status and the scope"
and `assertion_of_kind -> QuantityKind`. `QuantityKind` has families and a `recipe_role`
vocabulary (`control_setting`, `species_property`, ...).

**Resolver**: `controlled[]` entries carry `quantity`, `value`, `unit`, `recipe_role`,
`origin`, `scope`, `context_status`. So a *role* field exists - but it distinguishes
control-setting vs species-property, **not deposition vs measurement**. Nothing marks
"objective magnification" as an instrument setting.

**Consequence**: Yim Fig 7a (Series B) -> 3 Experiments. Three deposition cases invented from
one, by an optical setting.

**Status**: KEEP_BUT_CLARIFY (`recipe_role` is the right hook) + MISSING (no
measurement-condition role). Likely a **typed property/role**, not a new node class.
Severity HIGH.
