# The `unresolved entities` metric, decomposed

| count | meaning |
|---:|---|
| 61 | unresolved source entities in the corpus |
| 37 | **(a)** have at least one applicable condition in the source |
| 21 | **(b)** of (a), retained *every* such condition |
| 16 | of (a), retained some and withheld the rest as ambiguous |
| 24 | **(c)** the source supplies no applicable condition at all |
| 35 | carry at least one bound condition (the old headline numerator) |

(a) + (c) = 61 = the total, by construction.

## Why the old ratio was misleading

It divided the entities that happen to carry a condition by *all* unresolved entities, including the 24 for which no applicable condition exists in the paper. Those 24 can never move the numerator, so the ratio understated retention by construction. Against the population that can actually carry a condition, retention is 21/37 complete and 16/37 partial (partial meaning conditions were withheld as ambiguous, not lost).

## Unresolved-entity reasons

- `only one signal family (discrete_experimental_sweep)` — 20
- `only one signal family (continuous_trace)` — 9
- `conflicting signals: continuous_trace/multi_output_measurement` — 8
- `conflicting signals: multi_output_measurement/discrete_experimental_sweep` — 7
- `only one signal family (multi_output_measurement)` — 6
- `conflicting signals: discrete_experimental_sweep/multi_output_measurement` — 5
- `conflicting signals: discrete_experimental_sweep/continuous_trace` — 4
- `conflicting signals: ` — 2
