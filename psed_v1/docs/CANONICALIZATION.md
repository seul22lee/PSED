# Canonicalization — making figure data comparable across papers

How the PSED knowledge base turns heterogeneous, figure-derived numbers into a
**comparison-ready canonical layer** without ever overwriting the evidence it
came from.

Supersedes the design sketch in [COMPARABILITY_STRATEGY.md](COMPARABILITY_STRATEGY.md)
(phases P2 and P3 of that document are implemented here; P1 — families and
transforms in the ontology — shipped earlier and is reused, not replaced).

---

## 1. What "comparison-ready" means

A value is comparison-ready when **all four** of these hold:

1. its **quantity** resolves to an ontology `QuantityKind`;
2. its **unit** parses, and its dimension matches that quantity;
3. if it is normalized or dimensionless, the **exact normalization definition**
   is known — *which* denominator, from documentary evidence;
4. it therefore belongs to a named **ComparisonGroup**.

Anything that fails one of these stays in the dataset with a status and a
structured reason. It is never dropped, and never quietly coerced.

## 2. Raw vs recovered vs canonical vs derived

| Layer | Where it lives | Rule |
|---|---|---|
| **raw** | `03_corpus/extracted/{doi}/figure_data.json` | Never modified by anything in this pipeline. The canonical layer stores a copy plus a `json_pointer` and a `sha256` of the source file. |
| **recovered** | `03_corpus/extracted/{doi}/recovery/*.json` | New *evidence* about the raw data (a verbatim axis label read back off the figure). Additive, versioned, never a rewrite. Contains no data points. |
| **canonical** | `02_extraction/output/{doi}/canonical/curves.json` | The same values expressed in a comparison group's canonical quantity + unit. A separate array; the raw array is untouched. |
| **derived** | `projections` inside the same file | The axis expressed in a *second* comparison group, reachable only once a contextual value resolves (x/H + H → distance in µm). |

## 3. Direct vs contextual conversion

**Direct** needs nothing but the unit: same quantity kind, same physical
dimension, different unit.

```
nm ↔ µm ↔ Å ↔ m          Pa ↔ Torr ↔ mbar ↔ atm
s ↔ min ↔ h              °C ↔ K (affine)
Å/cycle ↔ nm/cycle       % ↔ 1
```

**Contextual** needs a value from somewhere else in the paper, and is refused
when that value cannot be pinned down:

```
x/L + L                → distance
x/H + H                → distance
GPC + cycle count      → thickness
thickness + cycle count→ GPC        (only under a recorded steady-growth assumption)
t(x)/t(0) + t(0)       → thickness
```

## 4. Dimensionless quantities

Three rules, all enforced in code and tested:

* **An empty unit is not automatically dimensionless.** In this corpus `""`
  overwhelmingly means "the extractor recorded no unit". `units.parse("")` raises
  unless the caller passes `allow_empty_as_dimensionless=True`, which only
  happens when a normalization definition resolved or the ontology declares the
  quantity dimensionless.
* **`unknown` ≠ `dimensionless`.** `a.u.`, `cps`, `counts` are rejected as
  unparseable, not silently treated as `1`.
* **`cycle` is its own base dimension.** `nm`, `nm/cycle`, a dimensionless
  fraction and a cycle count are mutually non-convertible. This is what stops
  `Å/cycle` from degrading to `nm` (which the old live pipeline did).

## 5. Normalization definitions

A normalized number is meaningless without its denominator. The ontology declares
**11 distinct definitions**; they are never merged into a generic "normalized
thickness" or "normalized distance".

| id | formula | denominator role | comparison group |
|---|---|---|---|
| `x_over_feature_height` | x/H | feature_height | normalized_spatial_position_by_feature_height |
| `x_over_channel_length` | x/L | channel_length | normalized_spatial_position_by_channel_length |
| `x_over_feature_depth` | x/d | feature_depth | normalized_spatial_position_by_feature_depth |
| `x_over_hydraulic_diameter` | x/D_h | hydraulic_diameter | normalized_spatial_position_by_hydraulic_diameter |
| `x_over_feature_width` | x/w | feature_width | local_aspect_ratio_position |
| `t_over_t_entrance` | t(x)/t(0) | entrance_thickness | entrance_normalized_thickness |
| `t_over_t_max` | t(x)/t_max | maximum_thickness | maximum_normalized_thickness |
| `t_over_t_planar` | t(x)/t_planar | planar_thickness | planar_normalized_thickness |
| `t_bottom_over_t_top` | t_bottom/t_top | top_thickness | step_coverage_bottom_to_top |
| `t_bottom_over_t_planar` | t_bottom/t_planar | planar_thickness | step_coverage_bottom_to_planar |
| `gpc_local_over_gpc_planar` | GPC(x)/GPC_planar | planar_growth_per_cycle | local_to_planar_growth_ratio |

Per spec §3.7, denominators **reuse existing quantity kinds** and add a semantic
role (`normalization_denominator_role`) rather than minting new kinds. `x/L` uses
`feature_length` with role `channel_length`; no `channel_length` quantity kind was
created.

## 6. Comparison groups

24 groups are declared. Two values may be compared **only** inside a shared
group. `similarity.curve_similarity()` returns `None` — an explicit refusal —
when no group is shared. There is deliberately no min–max fallback.

## 7. The transformation registry

Rules are **declared in the ontology** (`quantity_relations.transformation_rules`,
25 rules) and **bound to code** by `implementation_id` (10 implementations in
`canonical/rules.py`). There is no scattered `if`-chain.

The build fails when a declared rule has no implementation, an implementation has
no declaration, required units/context are missing, or a rule claims invertibility
without an inverse (`rules.validate_registry()`, gated by a test).

### Adding a new rule

1. Add an entry to `quantity_relations.transformation_rules` in
   `01_ontology/core.yaml` — id, version, type, implementation_id, input_units,
   output_unit, required_context, invertible, valid_domain, assumptions.
2. If it needs a new normalization, add it to `normalization_definitions` and
   point it at a `comparison_groups` entry.
3. `python3 01_ontology/build_ontology.py` — this **fails loudly** on any
   dangling reference.
4. If `implementation_id` is new, add an `Implementation(...)` to
   `IMPLEMENTATIONS` in `canonical/rules.py` (forward, optional inverse,
   optional validate).
5. Add a test to `canonical/tests/test_rules.py`.
6. `python3 -m unittest discover -s canonical/tests -t .` from `02_extraction/`.

## 8. Provenance model

Every canonical value carries a `TransformationExecution` with: the rule id and
version, the transformation type, the formula, every context value used (with its
**scope** and source file/location), the status, the confidence, the code version
and a deterministic timestamp. `canonical/validate.py` **fails the build** if a
canonical value exists without any of these.

## 9. Context resolution

Contextual values are searched narrowest-scope-first:

```
point → curve → series → panel → figure → experiment → method → paper
```

* the narrowest scope that answers wins outright (a curve-level channel height
  overrides a paper-level one, and that is *not* a conflict);
* within one scope, candidates are unit-normalized and compared: numerically
  equivalent candidates collapse to one value keeping all provenance;
* genuinely conflicting candidates return **ambiguous** — never a pick, never
  list order. A paper-level geometry value with three candidates cannot be
  broadcast onto every experiment.

## 10. Unresolved and ambiguous values

Nine statuses (`already_canonical`, `directly_convertible`,
`contextually_convertible`, `converted`, `ambiguous`, `missing_context`,
`unsupported`, `invalid`, `not_applicable`). Every non-success status carries an
`unresolved_reason` string; validation fails if it does not.

`invalid` is worth calling out: it marks a **unit/quantity dimension conflict**,
e.g. `growth_per_cycle` printed as `nm`. The missing `/cycle` is never assumed —
only a verbatim label that *shows* the per-cycle division (`"Thickness/cycles S/N
(nm)"`) can recover it, and then the recovery is recorded as evidence.

## 11. Worked examples

```
distance in µm ↔ nm          direct    length_unit_conversion, exact ×10ⁿ
x/L + L = 100 µm             context   denormalize_x_by_channel_length
                                       0.45 → 45.0 µm, L bound at figure scope
thickness 50 nm + N = 500    context   gpc_from_thickness_and_cycles → 0.1 nm/cycle
GPC 0.1 nm/cycle + N = 500   context   thickness_from_gpc_and_cycles → 50 nm
GPC + N + N₀ = 100           context   effective cycles = 400, assumption recorded
t(x)/t(0) + t(0) = 20 nm     context   denormalize_thickness_by_entrance
```

## 12. Running it

See [PIPELINE.md](PIPELINE.md) for the single documented workflow.
