# Twin / model-interface inventory (read-only)

`twin/twin_validation.py`.

## Assumptions the twin makes
| assumption | how it is expressed | consequence of a semantic change |
|---|---|---|
| candidacy is **observable-shaped**, not physical | `_member()` filters on measurand, coordinate, granularity, relevance, min_points - and deliberately **not** geometry ("membership by observable/scope only, never by outcome") | if Experiment becomes a case, `_member` must run over cases, and one case may carry several profiles |
| model validity is geometric | `DEFAULT_CRITERIA["model_validity"]["geometry"] = ["lateral_channel","vertical_structure"]` | geometry moving to case level changes which candidates are model-valid; today a mixed paper is judged by one paper-level label |
| a profile is decaying mouth-to-tail | `measured_profile()` returns None unless plateau >= 0.6*ymax and tail <= 0.6*plateau | correctly refuses non-profiles; this guard is **sound and should be preserved** |
| experimental vs simulated is already separated | targets come from `experiments.json`; SimulationRun entities never enter | **KEEP** |

## Evidence from the 27-vs-26 diagnosis
`langmuir.6b03119__Fig3a__exp02` was admitted by observable shape and then correctly
refused by `measured_profile()` because its x-axis is a tube *diameter*, not a mouth-to-tail
coordinate. The twin behaved correctly; the brittle assertion `n_candidates == len(COMPS)`
is what failed.

## Propagation risk
Changing Experiment identity changes the twin candidate population directly
(`_targets()` reads `experiments.json`). Any case-level consolidation will reduce candidate
counts and must be re-baselined deliberately, not silently.
