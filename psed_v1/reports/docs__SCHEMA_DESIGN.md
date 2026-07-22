# Schema design — separating the layers (for review)

The coverage audit (156 analysis-ready experiments) showed our extraction is strong
on the **measurement/model** layer (twin params 66–70%) and weak on the **recipe**
layer (species 0%, purge_time 1%, ncycles 19%). That's not an extraction bug — it's
a sign the schema conflates things that live at different levels. This doc proposes
a five-layer model and, in particular, the **Recipe vs Measurement** split for you
to weigh in on before we change the ontology further.

Fix #1 (precursor properties → ontology species individuals) is **already done** and
is the bottom layer below.

## The five layers

```
  ┌──────────────────────────────────────────────────────────────┐
5 │ MODEL            kinetic model + its parameters (Ylilammi,     │  parameterises
  │                  Langmuir): k1,k2,GPC0,reaction_probability…   │  the TWIN
  ├──────────────────────────────────────────────────────────────┤
4 │ MEASUREMENT      one observed curve/point (a figure series):   │  ← what we have
  │  (=Experiment)   thickness-vs-depth, coverage, PD50…           │    today
  ├──────────────────────────────────────────────────────────────┤
3 │ RECIPE / PROCESS the deposition protocol: chemistry + timing   │  ← the NEW object
  │                  (dose/purge per reactant) + ncycles + super-  │    (drives reactor)
  │                  cycle + temperature + structure               │
  ├──────────────────────────────────────────────────────────────┤
2 │ CHEMISTRY        material → (precursor, coreactant) mapping     │  fix #2
  │                  (Al2O3 ← TMA + H2O)                            │
  ├──────────────────────────────────────────────────────────────┤
1 │ SPECIES          precursor / coreactant individuals with       │  ← fix #1 DONE
  │                  intrinsic props (molar_mass, diameter, atoms) │
  └──────────────────────────────────────────────────────────────┘
```

Key relationships:
- one **Recipe** (3) is *measured_by* many **Measurements** (4) — a growth yields a
  thickness profile *and* a coverage curve *and* a GPC-vs-dose sweep.
- a **Recipe** (3) *uses* a **Chemistry** (2), which *references* **Species** (1).
- a **Measurement** (4) may *validate* a **Model** (5); a **Model** *parameterises*
  the twin. Model-paper "experiments" (Ylilammi) are really layer-5 objects, not
  layer-3 recipes.

## Why the split matters (the audit, explained)

| Symptom | Cause | Fixed by |
|---|---|---|
| species 0% | precursor identity is layer-1/2, stored nowhere per-experiment; profile lists a *union* of all precursors | fix #1 (done) + fix #2 |
| mass/diameter repeated 104× | intrinsic species props (layer 1) stored as per-experiment conditions (layer 4) | **fix #1 (done)** |
| purge 1%, ncycles 19% | recipe timing (layer 3) lives in the **methods text**, but we extract figures/captions | fix #3 (scope) |
| duplicate recipes when we lift | many measurements (layer 4) share one recipe (layer 3); we lift per-measurement | Recipe/Measurement split |

## DECISION (made): 1 recipe per experiment
We chose **1:1 experiment↔recipe** — each experiment carries its own `recipe` block —
over the dedup/grouping options below. Rationale: a dose sweep (Fig. 5, 92 points) has
a *different dose per point* = genuinely a different recipe, so grouping would be wrong;
and it removes the ambiguous "is this parameter a recipe difference?" rule. We keep
**recipe (reactor process: chemistry + dose/purge + ncycles + temperature)** separate
from **structure (sample H/W)** — both ride on the experiment, but only the recipe maps
to the reactor/Argonne JSON. Implemented in `s08` (`x["recipe"]`), read via
`kb_service.get_recipe` / `list_recipes`. The options below are kept for the record.

## (superseded) The Recipe ↔ Measurement split

**Proposal:** make **Recipe** a first-class object that several Measurements point to,
instead of lifting one Recipe per measured curve.

- A **Recipe** = `{material, chemistry(precursor,coreactant), reactants[dose/purge/p],
  cycle_sequence, supercycle, ncycles, temperature, structure}`.
- A **Measurement** (today's resolved "experiment") keeps its curve + measurand +
  coordinate + provenance, and gains a `recipe_ref`.
- **Dedup**: measurements from the same figure/growth with identical chemistry +
  conditions collapse to one Recipe (like our figure-level condition sharing already
  does — this is the same grouping, promoted to an object).

Two ways to realise it — pick one:

**Option A — Recipe as a derived index (lightweight, reversible).**
Keep `experiments.json` as-is; add `recipes.json` per paper = the deduped Recipes,
each listing the `exp_id`s that measured it. `s08` builds it from the experiments it
already resolves. *Pros:* no disruption, easy to revert, dashboards/twin read either.
*Cons:* two files to keep in sync.

**Option B — Recipe as the primary object (clean, larger change).**
Restructure so a paper's output is `recipes:[ {recipe, measurements:[...]} ]`.
*Pros:* the graph matches reality (recipe→measurements); no duplication. *Cons:*
touches s09/KG, dashboards, similarity, evaluate — a real migration.

**Recommendation: Option A now.** It gives the Recipe object + dedup + the agent/twin
bridge immediately, with near-zero risk, and leaves Option B as a later promotion if
the recipe layer becomes central. The Recipe *class* (`recipe.py`) is already
Argonne-interoperable, so Option A is mostly a `build_recipes.py` that groups + dedups.

## Where model papers fit (important nuance)

Ylilammi's 108 "experiments" are **model curves**, not reactor recipes — their
"reactant A/B" are abstract with model-given properties. Under this design they are:
- layer-5 **Model** parameterizations (they give k, GPC0, reaction_probability, and
  the generic A/B mass/diameter that parameterise the twin), and
- layer-4 **Measurements** of the model's predicted profiles.
They should **not** be forced to have named species or reactor recipes. So the recipe
layer's low coverage is partly *correct*: most of our current corpus isn't recipes.
The recipe layer will fill as we ingest **experimental** papers (methods text + named
chemistry). This is also the argument for fix #3 (methods-text scope) + scaling.

## Migration / what changes where (if you approve Option A)

1. **`recipe.py`** — already has the object + Argonne interop + `from_experiment`.
   Add `dedup(recipes)` (group by chemistry+conditions).
2. **`0706_pipeline/build_recipes.py`** (NEW) — read resolved experiments → deduped
   `recipes.json` per paper, each with `measurements:[exp_id…]` and `completeness`.
3. **`kb_service.py`** — `get_recipe(id)` / `list_recipes(filter)` read `recipes.json`.
4. **`s08`** — stop emitting per-experiment `molecular_mass`/`precursor_molecular_diameter`
   for **named-species** (non-model) experiments (they're layer-1 now); keep them for
   model experiments but tag `model_input:true`. *(Deferred until we have named-species
   papers; today it's all model.)*
5. **fix #2** — `s06` study profile emits a `chemistry` map material→(precursor,
   coreactant); unlocks species resolution for experimental papers.
6. **fix #3** — extend evidence scope / a recipe pass to read dose/purge/ncycles from
   the methods paragraph.

## Open questions for you
1. **Option A vs B** for the Recipe/Measurement split? (I recommend A.)
2. For model papers, keep the generic A/B mass/diameter as tagged `model_input`, or
   drop them from the twin path once species-grounding (fix #1) is preferred? (I'd keep
   them tagged — they're the only grounding when no species exists.)
3. Priority order of fix #2 (chemistry mapping) vs fix #3 (methods scope) — #2 is
   cheaper and unlocks species; #3 needs a new extraction pass.
