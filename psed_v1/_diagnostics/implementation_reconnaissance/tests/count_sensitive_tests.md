# Count-sensitive assertions

Hard numeric literals found in `tests/`:

| file:line | assertion | nature |
|---|---|---|
| `regression/test_geometry_model_params.py:128` | `len(ids) == 1` (aspect-ratio fan-out shares one evidence id) | **semantic** — deduplication invariant |
| `regression/test_m2_design.py:336` | `len(res["family_ranges"]) == 3` | snapshot of the chemistry families present |
| `regression/test_twin_validation.py:63` | `len(tv.STATUS) >= 15` | lower bound on a closed vocabulary |
| `regression/test_twin_validation.py:65` | `len(tv.LOCI) == 6` | fixed vocabulary size |
| `regression/test_provenance.py:288` | `len(w) == 2 and w[0] != w[1]` | **semantic** — a window is a genuine range |
| `regression/test_m2_chemistry.py:78` | `len([a for a in alts if a["resolved"]]) == 2` | snapshot |
| `regression/test_chemistry_params.py:70` | `len(byk) == 4` | snapshot of quantity kinds |
| `regression/test_card_temperature.py:42-43` | `_scalar([175,300]) == 175/300` must be False | **semantic** — endpoint never used |
| `canonical_layer/test_granularity_and_axes.py:266` | `len({physical_case_id}) == 1` per figure | **semantic**, but scoped to a figure |
| `canonical_layer/test_granularity_and_axes.py:355,357` | summary count == set size | self-consistency |
| `canonical_layer/test_stage0_regression.py:116,120` | `sum(case_count) <= 1` per shared event; `case_count <= 1` per entity | **semantic**, per-entity scope |
| `canonical_layer/test_stage0_regression.py:146` | `experimental_case_count <= 1` for representation entities | **semantic**, per-entity scope |

## The distinction asked for

**Scientific invariants** (would remain true under any correct model): no experiment count
from point count; a PlotSeries is never an Experiment; observations are not experiments;
imported literature keeps both papers; unknown entities are preserved unsplit and unpromoted;
no observation lost; a window endpoint is never a scalar; multi-output channels do not each
mint a case.

**Brittle count snapshots** (freeze the current numbers): the twin candidate count
(`test_twin_validation.py`, known brittle), `len(res["family_ranges"]) == 3`,
`len(byk) == 4`, `len(alts resolved) == 2`, `len(tv.LOCI) == 6`.

**Semantically right but scoped to the current model**: `test_stage0_regression.py:141`
("representations do not duplicate the underlying case") asserts `case_count <= 1` **per
entity**. Yim Fig 9 has 18 entities each with exactly 1 case, so the test passes while the
6 underlying measurements are counted 18 times. The assertion's scope is the entity;
the scientific claim it names is about the measurement.

Same pattern at `test_granularity_and_axes.py:266`: `len({physical_case_id}) == 1` is
asserted **per printed figure**, which is exactly the locality that `_events` guarantees by
construction.
