# P131b step 3: the six multi-paper `other` labels

Run: `python3 psed_v2/ontology/pending_decide.py --labels "b_film;wall temperature;wavelength range;base pressure;k;p_d"`.
Each label became a candidate pending.csv row by code (`pending_decide.candidate()`: the `other[...]` records whose printed label is equal
up to case), then the P98 rules ran unchanged: (a) records in ≥ 2 papers; (b) a Cremers 2019 section marked sure (no candidate has one);
(c) a species, structure or method named by an experimental run (quantities never qualify); (d) converts_to an accepted entry (none set).

| label | id | records (papers) | unit, dimension | role | rule fired | decision |
|---|---|---|---|---|---|---|
| b_film | `b_film` | 4 (yim20, yim22, yli18) | (none), dimensionless | model_parameter | a | accepted |
| wall temperature | `wall_temperature` | 2 (mat22, mat23) | °C, temperature | condition | a | accepted |
| wavelength range | `wavelength_range` | 3 (mat23, yim20) | nm, length | condition | a | accepted |
| base pressure | `base_pressure` | 2 (ela03, mat22) | Torr, pressure | condition | a | accepted |
| P_d | `p_d` | 10 (yim20, yim22) | 1/s, inverse_time | model_parameter | a | accepted |
| k | none | 3 (ela03 `k` ×2, yim20 `K` ×1) | s^-1/2 (not in units.yaml) and Pa-1 (inverse_pressure) | | stopped: two concepts | not a row |

- `k`: the case-folded label joins two quantities. ela03's `k` is the coefficient of a √t fit (s^-1/2). yim20's `K` (Pa-1) is the
  adsorption equilibrium constant, already an alias of the existing entry `adsorption_equilibrium_constant`. Per paper, each is one paper.
  The script stops on two dimensions and writes no row. Not resolved here; the yim20 `K` record stays `other[K]`.
- `p_d` needed the unit `1/s`: units.yaml had no inverse-time row, so `1/s` and `1 s-1` had no dimension. P131b adds
  `{symbol: 1/s, variants: [1/s, s-1, 1 s-1, s^-1, s⁻¹], dimension: inverse_time}` to units.yaml and `inverse_time` to the units: block.
- Rule-made fields to check by eye: id = the label in snake case; definition = the printed label, the record count and the first record's
  statement verbatim; cq blank; category `measurement` (export's rule for a quantity whose cq does not name a structure).
- The five accepted rows were merged into ontology.yaml by `merge_pending.py` with `from_other: [<printed label>]`; `facts.write()`
  re-keys those `other[...]` records (21 records, verify/d14/REPORT.md).
- Not in the six, found by the same count: `chip size` (yim20, gao15; 2 setting records, units mm and none) is a seventh multi-paper
  `other` label. Not decided.
- Veto: name the id; `merge_pending.py` does not delete, so a veto is a hand removal of the yaml block and its `from_other` re-key.
