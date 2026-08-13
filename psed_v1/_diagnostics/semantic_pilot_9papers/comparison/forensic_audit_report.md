# Forensic audit — read-only, no resolver changes

State audited: the working tree exactly as it stands. **No code was changed during this
audit and no output was regenerated**, so every number below is what is on disk.

---

## 0. First finding: the on-disk state is internally inconsistent

The `design_signature` edit landed **partially**. Three files were meant to change together;
two did and one did not:

| file | intended change | landed? |
|---|---|---|
| `code/pilot_design.py` | `design_signature()`, `process_step()`, `material=` on `design_from_sweep` | **yes** — 10/10 designs carry `signature` |
| `code/pilot_cases.py` | pass `material` through, write `design_signature` onto each branch | **no** — 0/56 branches carry `design_signature` |
| `code/pilot_semantics.py` | key the merge on `b.get("design_signature")` | **yes** |

The consequence is worse than the state it was meant to fix. The merge key reads a field
nothing writes, so `tuple(b.get("design_signature") or ())` evaluates to `()` for every
branch and the key collapses to:

```
(printed_figure, (), branch_value)          # the quantity is gone entirely
```

JES therefore moved **52 → 46 cases** between the snapshot and now — not an improvement but
a *further* loss of design identity. Everything in §1 below must be read in that light.

**Nothing else moved**: am 27, Yim 14, d0ra09876k 100, and the other five are identical to
the pre-repair snapshot.

---

## 1. JES — merge audit

### Design inventory (signatures are computed correctly)

| panel | quantity | process step | material | branches |
|---|---|---|---|---|
| 4a | exposure_time | `precursor_dose` | — | 6 |
| 4b | purge_time | `precursor_purge` | — | 6 |
| 4c | pulse_time | `plasma_exposure` | — | 6 |
| 4d | purge_time | `plasma_purge` | SiO2 | 4 |
| 4e | exposure_time | `precursor_dose` | — | 4 |
| 4f | purge_time | `precursor_purge` | — | 4 |
| 4g | pulse_time | `plasma_exposure` | — | 6 |
| 4h | purge_time | `plasma_purge` | Al2O3 | 4 |
| 5a | deposition_temperature | — | SiO2 | 8 |
| 5b | deposition_temperature | — | SiO2 | 8 |

Total = **56 branch observations**; Fig 4 = **40**, matching the gold anchor exactly.
`process_step` separates precursor purge from plasma purge correctly. **Material is
resolved for only 2 of 10 designs** — the caption's `(a)–(d) … SiO2 … (e)–(h) … Al2O3`
range clauses are not reaching the design.

### The 33 merge edges, classified

| edge | quantity a / b | step a / b | verdict | why |
|---|---|---|---|---|
| 4a ↔ 4e | exposure_time / exposure_time | precursor_dose / precursor_dose | **UNSUPPORTED** | same quantity and step, but 4a is the **SiO2** dose and 4e the **Al2O3** dose. The caption states this; the material never reached the design, so the guard could not fire. |
| 4b ↔ 4d | purge_time / purge_time | precursor_purge / **plasma_purge** | **UNSUPPORTED** | different recipe steps |
| 4b ↔ 4h | purge_time / purge_time | precursor_purge / **plasma_purge** | **UNSUPPORTED** | different step *and* different material |
| 4b ↔ 4c | purge_time / **pulse_time** | precursor_purge / plasma_exposure | **UNSUPPORTED** | **different quantities entirely** — only possible because the broken key dropped the quantity |
| 4b ↔ 4g | purge_time / **pulse_time** | precursor_purge / plasma_exposure | **UNSUPPORTED** | as above |
| 4b ↔ 4f | purge_time / purge_time | precursor_purge / precursor_purge | **VALID** by signature, but see below | same quantity and step; still crosses SiO2→Al2O3, so it is **UNSUPPORTED on the material axis** |
| 5a ↔ 5b | deposition_temperature ×2 | — | **VALID** | the intended case: two outputs (n and GPC) of one temperature branch |
| 3 × Fig 2b/3 edges | — | — | **VALID** | explicit `same_sample` citing figure 3 — the PDF says "on the same sample" |

**Totals: 4 VALID edge classes, 6 UNSUPPORTED edge classes.** Of the 33 concrete edges,
24 are cross-design.

### Answers to the four explicit checks

- **SiO2 ↔ Al2O3 merges: YES, present.** 4a↔4e and 4b↔4f.
- **precursor purge ↔ plasma purge: YES, present.** 4b↔4d and 4b↔4h.
- **Merges from both sides having unknown material: YES — this is the dominant cause.**
  8 of 10 designs carry `material = None`, so `material=?` matches `material=?`.
- **Merges from both sides having unknown process step: no.** `process_step` is populated
  wherever the axis label names a step; the two `deposition_temperature` designs have
  `step=None` on both sides, which is correct (temperature belongs to no single step) and
  their merge is the valid one.

---

## 2. am.2016.182 — root cause of 50 → 27

**Not a bug. The mechanism is the intended one, and the merges are valid.**

Three designs are built: Fig 1a `exposure_time` (5 branches, Pt), Fig 2a and Fig 2b
`deposition_temperature` (4 and 3 branches, Pt). Material **is** resolved here, and both
Fig 2 designs share the signature `(deposition_temperature, step=-, °C, Pt)`.

12 merge edges: **10 same-design DESIGN_BRANCH_LINK, 2 SUPPORTED** (the pre-existing
enumerated-settings rule).

The collapsed groups:

| case | panels | conditions | verdict |
|---|---|---|---|
| −015 | 2a, 2b | T = 80 °C, precursor HDMP | **VALID** — GPC and resistivity at one temperature branch |
| −016 | 2a, 2b, 2c | T = 100 °C, HDMP | **VALID** — the anchor join, now with XPS |
| −017…−020 | 2a, 2b | T = 120/150/200/250 °C, HDMP | **VALID** |
| −021 | 2a, 2b, 2c | T = 300 °C, HDMP | **VALID** |
| −023…−025 | 2a, 2b | T = 250/275/300 °C, **MeCpPtMe3** | **VALID** — and correctly kept apart from the HDMP branches at the same temperatures |

**This is the JES Fig-5 pattern working correctly**: one temperature branch measured as
GPC *and* as resistivity is one case with two outputs, not two cases. The precursor is part
of the case-defining conditions, so the two precursor series never cross.

**Verdict: 50 → 27 is a genuine improvement, not a regression.** Nothing here is
UNSUPPORTED or AMBIGUOUS. The earlier 50 counted each output panel separately.

---

## 3. d0ra09876k — root cause of 50 → 100

**Not double generation.** The duplicate-generation scan over all nine papers found
**0 duplicate `(entity, quantity, value)` branches**; there is exactly one case-generation
path. The 100 splits as **90 design-branch + 10 whole-curve** cases.

### The 90 branches come from 9 designs — and 53 of them are wrong

| figure | panel | quantity | measurand | branches | verdict |
|---|---|---|---|---|---|
| **2** | a | `temperature` | **Weight (%)** | 19 | **UNSUPPORTED** |
| **2** | a | `temperature` | **Weight (%)** | 18 | **UNSUPPORTED** |
| **2** | a | `temperature` | **Weight (%)** | 16 | **UNSUPPORTED** |
| 3 | a | deposition_temperature | growth_per_cycle | 10 | VALID |
| 3 | a | deposition_temperature | growth_per_cycle | 10 | VALID |
| 3 | c | pulse_time | growth_per_cycle | 5 | VALID |
| 3 | c | pulse_time | growth_per_cycle | 5 | VALID |
| 3 | d | purge_time | growth_per_cycle | 3 | VALID |
| 3 | d | purge_time | growth_per_cycle | 4 | VALID |

**PDF evidence.** Figure 2 caption: *"Top: **TG analysis** of [Y(DPfAMD)3] (black),
[Y(DPDMG)3] (blue) and [Y(DPAMD)3] (red). Bottom: **vapor pressure measurements** for all
three complexes."*

Figure 2 is **thermogravimetry of three precursor complexes** — an instrument ramps the
temperature and records mass loss. Its x axis is a **MEASUREMENT_COORDINATE**, exactly like
the JES Fig 2 cycle-number progression, and its y axis is a **species property**, not a film
property. It produces **53 spurious deposition cases** for a figure in which nothing is
deposited.

**Root cause.** `axis_role()` sees the bare quantity `temperature`, whose ontology
`recipe_role` is `control_setting`, and returns `CASE_DEFINING_PROCESS_SETTING`. It never
consults the measurand. The species-property gate that already exists in
`pilot_roles.is_species_property` is applied to material assertion and case minting for
*whole-curve* entities, but the design path bypasses it.

Fig 3's 37 branches are legitimate: GPC vs temperature, vs pulse time, vs purge time — the
paper's real saturation study. Note that Fig 3a and 3c and 3d each produce **two** designs
(two curves per panel), which is why 3a gives 10+10 rather than 10.

### The 10 whole-curve cases

Behind them: **9 `MultiOutputMeasurement` + 1 `ExperimentSeries`** entities across
figures 2, 3, 4, 5, 6, 7. They are XPS/XRD/AFM/capacitance panels — characterisation, not
sweeps. They do not duplicate the design branches (different figures, except two on Fig 2
and one on Fig 3 that come from different entities). **Verdict: not duplicates**, but three
of them sit on Fig 2 and therefore inherit the same TGA-context problem.

**Corrected expectation.** Removing the three TGA designs leaves **37 branch observations**
from the real saturation study plus the characterisation cases — on the order of **45**,
not 100. The exact number needs the Fig 3 sub-design question resolved (see §5.3).

---

## 4. Yim — exactly why 14, not 11

Every current case mapped onto the Table-1 nominal fingerprint (recipe, height, layout,
cycles). **The gold fingerprinting reproduces 11 nominal cases from the 16 specimens**, and
the BASE group is exactly `2, 4, 5, 6, 8, 12`.

| current case | figures | samples | gold case(s) |
|---|---|---|---|
| −001 | 3, 5 | 11 | G07 ✓ |
| −002 | 7, 8, … | **12, 2, 4, 5, 6, 8** | **G02 (BASE) ✓** |
| −003 | 9 | 7 | G04 ✓ |
| −004 | 9 | 9 | G05 ✓ |
| −005, −006, −007 | 9 | *none* | unbound |
| −008, −009, −010 | 11 | 12, 13, 14 | **G02 + G08 + G09** ← ambiguous |
| −011, −012, −013 | 11 | 12, 15, 16 | **G02 + G10 + G11** ← ambiguous |
| −014 | 6 | *none* | unbound |

**The BASE case already works**: case −002 correctly holds all six BASE specimens across
figures 7 and 8. That half of the repair is done.

### The exact 14 → 11 discrepancy

Two groups of three, both in Fig 11:

- **−008/−009/−010** each carry *all three* Series E specimens (12, 13, 14) instead of one
  each. Three cases where the gold is three **different** cases — so the count happens to
  be right but **every binding is wrong**: each should be one specimen (12→BASE, 13→G08,
  14→G09).
- **−011/−012/−013** the same for Series F (12, 15, 16).

Because 12 appears in both groups and is a BASE specimen, correct binding would fold
−008-or-−011 (whichever carries the 0.1 s / 4 s baseline) into the existing BASE case,
removing **2** cases. The remaining **1** comes from the four unbound cases on Figs 9 and 6:
three Fig 9 cases have no specimen at all and one of them is the shared sample-8 BASE
profile.

**14 → 11 = 2 (Fig 11 baselines folding into BASE) + 1 (Fig 9 sample-8 profile folding
into BASE).**

**Root cause.** The rejected sentence-group patch is confirmed **not applied**: the value
join still pools a figure's whole caption, so Fig 11's specimen set is `{12,13,14,12,15,16}`
and Fig 9's is `{7,8,9,8,10,11}`. With six candidates and a column that does not distinguish
them, `value_join_specimens` declines, and every curve keeps the whole caption list.

### Recorded as instructed

- **Fig 9 producing 5 unique cases is CORRECT** (Series C ∪ Series D = {G02, G04, G05, G06,
  G07}, sharing sample 8). The current output reaches 5 Fig-9 cases, though 3 of them are
  unbound rather than specimen-bound.
- **The existing test `yim: Fig 9 yields 6 cases, not 18` is scientifically WRONG** and is
  the single failing test (84/85). It encodes the pre-repair behaviour. Classification:
  **REWRITE** to 5, with the shared-sample-8 justification.
- **`x/H` is classified `MEASUREMENT_COORDINATE`** — recorded as a bug. It should be a
  spatial/profile coordinate. The canonical quantity ids (`spatial_coordinate`,
  `dimensionless_distance`, `depth`, `position`, `feature_depth`) all classify correctly;
  only the literal axis-label form misses. Not fixed.

---

## 5. Remaining generic architecture problems these audits revealed

**5.1 Design identity is computed but not carried.** The signature exists on the design and
never reaches the branch, and the merge key reads it anyway. Until the three files agree,
the merge key is strictly weaker than before the change. *(This is the inconsistent-edit
state, and it is the first thing to repair.)*

**5.2 Material does not reach the design.** 8 of 10 JES designs have `material = None`,
which is what lets the SiO2 and Al2O3 halves of one saturation figure merge. The caption
range clauses `(a)–(d) … SiO2` / `(e)–(h) … Al2O3` are parsed by `panel_clauses` but the
material they carry is not propagated into `design_from_sweep`. **A design signature whose
material is unknown on both sides must not be treated as matching** — unknown is not equal.

**5.3 One panel can hold several designs, and they are not distinguished.** Fig 3a of
d0ra09876k yields two `deposition_temperature` designs (two curves), and JES Fig 5a/5b give
one design each. There is no rule saying when two curves in one panel are two designs versus
one design measured twice. This is the same ambiguity in both papers.

**5.4 The axis-role classifier ignores the measurand.** A `temperature` axis against
`Weight (%)` is thermogravimetry; against `growth_per_cycle` it is a deposition-temperature
sweep. `axis_role()` sees only the x quantity. The species-property gate that would catch
this already exists but is not consulted on the design path. **This single omission produces
53 of d0ra09876k's 100 cases.**

**5.5 The value join still pools a whole caption.** Confirmed not applied. It blocks the
last 3 Yim over-splits and mis-binds all 6 Fig 11 curves.

**5.6 Merge validity is not checked against the design.** `resolve_cases` tests condition
compatibility but never asks whether two candidates belong to the same design. A
cross-design merge with non-contradicting conditions passes silently — there is no invariant
that would have caught the 24 bad JES edges.

---

## Summary table

| item | finding | severity |
|---|---|---|
| on-disk consistency | partial edit; merge key reads a field nothing writes | **blocking** |
| JES cross-design merges | 24 of 33 edges; SiO2↔Al2O3 and precursor↔plasma purge both present | **severe** |
| JES Fig 4 branch count | **40**, matches gold exactly | correct |
| am 50 → 27 | valid; one temperature branch measured two ways is one case | **correct, not a regression** |
| d0ra09876k 50 → 100 | 53 spurious branches from three TGA precursor curves | **severe** |
| d0ra09876k duplicate generation | none — 0 duplicates across all nine papers | correct |
| Yim BASE case | 6 specimens correctly in one case | correct |
| Yim 14 → 11 | 2 Fig-11 baselines + 1 Fig-9 sample-8 profile | **known, unfixed** |
| Yim Fig 9 = 5 | correct; the test expecting 6 is wrong | test **REWRITE** |
| `x/H` axis label | classified as measurement coordinate | minor, recorded |
| curves / points | 100 % preserved on all nine | correct |
