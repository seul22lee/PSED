# Comparability Strategy — comparing related-but-not-identical quantities

**Status: design only (no code yet).** How to let the KB compare experiments whose
axes measure the *same underlying thing* expressed differently — e.g. `film_thickness`
vs `normalized_thickness` vs `step_coverage` on the y-axis, or `spatial_coordinate` (µm)
vs `dimensionless_distance` (x/H) vs `aspect_ratio` on the x-axis.

## 1. The problem

Today an experiment carries a `comparability_signature` = `independent ~ measurand`
built from **exact** quantity ids, e.g. `spatial_coordinate ~ film_thickness`. Two
experiments overlay only if these strings match. But:

- `film_thickness` (nm), `normalized_thickness` (–), `growth_per_cycle` (nm/cyc) all
  report **how much film grew** — physically the same measurand, different encoding.
- `spatial_coordinate` (µm), `dimensionless_distance` (x/cavity-height), `aspect_ratio`
  (x/width) all locate **the same position** along a HAR feature.

Exact-match says "not comparable." A researcher says "of course they are — normalize
one." The fix must be **ontology-driven**, not string equality.

## 2. Core idea — families + transforms + tiers

Three ontology-grounded pieces:

1. **Quantity family (a shared *measurand class*)** — group quantities that quantify
   the same physical concept.
2. **Transforms between family members** — the equation (and the *bridge quantity* it
   needs) that converts one member into another.
3. **Comparability tiers** — a graded verdict on *how* comparable two experiments are
   and *what is missing* to align them.

## 3. Ontology model (what to add to `core.yaml`)

### 3a. Measurand families (new individuals + `family` tag on each quantity)

| Family | Members | Common basis (canonical form) |
|--------|---------|-------------------------------|
| **FilmAmount** | film_thickness, normalized_thickness, growth_per_cycle, areal_mass_density, step_coverage* | normalized thickness (0–1) |
| **Coverage** | surface_coverage, maximum_surface_coverage, saturated_coverage | fractional coverage (0–1) |
| **Position** | spatial_coordinate, dimensionless_distance, aspect_ratio, penetration_depth | dimensionless distance x/H |
| **Dose** | exposure, plasma_exposure_time·pressure, partial_pressure×pulse_time | exposure (Pa·s) |
| **Rate** | growth_per_cycle, growth_rate, deposition_rate | growth_per_cycle (nm/cyc) |

\*step_coverage is a *ratio of thicknesses at two positions* — it lives in FilmAmount
but is itself a derived comparability metric (see §7).

Each `quantity_kind` gets `family: <FamilyId>`. Compiled by `build_ontology.py`.

### 3b. Transforms (extend `defined_by`; add a `normalizes` edge type)

Every transform is `target = source ⊙ bridge`, with the **bridge quantity** named so the
app knows what it must find in the record to apply it, plus a validity note.

| Transform | Bridge quantity | Notes |
|-----------|-----------------|-------|
| normalized_thickness = film_thickness / t_ref | reference/saturation thickness | ref = thickness at aperture or saturated value |
| growth_per_cycle = film_thickness / cycle_number | cycle_number | already in `controlled` for most records |
| dimensionless_distance = spatial_coordinate / feature_height | **feature_height** | *present as a condition today* → works now |
| aspect_ratio = spatial_coordinate / feature_width | feature_width | present today |
| areal_mass_density = film_thickness × mass_density | material density | ties into value↔value/area bridging |
| exposure = partial_pressure × pulse_time | (both present) | already implemented as `derive_quantities` |

This **generalizes** the value↔value/area bridge already scoped: per-area, per-cycle,
and normalization are all "target = source ⊙ bridge." One mechanism.

### 3c. Reuse what exists
- `specializes` (taxonomy: pulse_time ⊂ time) — orthogonal, keep.
- `same_as` (deposition_rate = growth_rate) — the trivial (identity) transform.
- `defined_by` (13 equations) — already holds several transforms; extend, don't replace.

## 4. Comparability tiers (the graded verdict the app returns)

| Tier | Condition | Action | Example |
|------|-----------|--------|---------|
| **0 identical** | same quantity + same unit | direct overlay (today's behavior) | thickness(nm) vs thickness(nm) |
| **1 unit-convert** | same quantity, different unit | scale factor | thickness nm vs µm |
| **2 aligned** | same family, transform's bridge present in *both* records | transform → overlay in common basis | thickness vs normalized_thickness (t_ref known); x µm vs x/H (feature_height known) |
| **3 latent** | same family, bridge **missing** | flag "comparable in principle — missing `<bridge>`" | thickness vs normalized_thickness with no reference thickness |
| **4 shape-only** | different family | normalized 0–1 shape overlay + warning (today's mixed-quantity fallback) | thickness vs pressure |

Tiers 0–2 are *quantitative* comparisons; tier 3 tells the user exactly what datum
would unlock the comparison (a research-actionable message); tier 4 is the honest
"shapes only" floor.

## 5. Pipeline changes (deterministic, from the ontology — later)

1. Rename `property_of_interest` → **`measurand`** (y); keep `independent_var` → rename
   to **`coordinate`** (x) for symmetry.
2. Stamp `measurand_family` and `coordinate_family` on each experiment (lookup from the
   compiled ontology).
3. Replace the exact `comparability_signature` with a **`comparability_key`** =
   `(coordinate_family, measurand_family)` — the coarse "could these compare" grouping —
   while keeping the exact quantities for tier detection.
4. Record which bridge quantities are present (so tier 2 vs 3 is decidable offline).

## 6. Comparison-app changes (later)

Given N selected experiments:
1. Compute the **tier** of each against a chosen reference (or pairwise).
2. Pick the family's **common basis**; **transform** each curve into it when the bridge
   is present (tier ≤2); otherwise show the tier-3 "missing bridge" note or tier-4
   shape-only normalization.
3. Overlay in the common basis, axis labeled with the canonical form + a badge showing
   the tier and any transform applied ("normalized by feature_height").

This is a strict superset of the current unit-aware overlay — tier 0/1 = today's
"true-units" path, tier 4 = today's "normalized shapes" path; tiers 2–3 are the new
middle that the ontology unlocks.

## 7. ALD-specific notes / risks

- **x-axis alignment works *today*** for the common case: `spatial_coordinate` ↔
  `dimensionless_distance` needs `feature_height`, which is already a `controlled`
  condition on the profiles. This is the highest-value, lowest-risk first win.
- **Normalization reference ambiguity**: `normalized_thickness = thickness / t_ref` —
  what is `t_ref`? Saturated thickness? Thickness at the aperture? The ontology must
  name the reference explicitly per transform, or normalization will silently differ
  between papers.
- **step_coverage / conformality** is not just a member — it's a *reduction* of a
  thickness profile (thickness at depth ÷ thickness at mouth). Worth modeling as a
  derived measurand computed from a FilmAmount profile, so an experiment reporting a
  raw profile can be compared against one reporting only a step-coverage number.
- **False friends**: `penetration_depth` is in Position but is an *output* (a scalar
  extracted from a coverage profile), not a coordinate. Family membership must not imply
  interchangeable axis role — keep family (what) and axis role (how used) independent.

## 8. Phased plan

- **P1 — ontology**: add families + transforms (with bridge + validity) to `core.yaml`;
  compile `family` onto quantity_kinds. No app change; `evaluate_relations.py` gains a
  "family coverage" check.
- **P2 — pipeline**: rename to `measurand`/`coordinate`; stamp families + bridge
  availability + `comparability_key`.
- **P3 — app**: tiered comparability + transform-on-overlay (generalizes value/area +
  the existing unit-aware overlay).

Start at P1; each phase is independently useful and testable.
